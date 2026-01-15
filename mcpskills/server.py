"""MCP (Model Context Protocol) Server Implementation.

This module implements an MCP server using FastMCP, providing financial research tools:
- Stock market data retrieval and technical analysis
- SEC filing extraction (10-K reports)
- Stock chart generation with technical indicators
- Fundamental ratio analysis and peer comparisons
- Trade blotter database queries

The server follows the Model Context Protocol specification as defined at:
https://modelcontextprotocol.io/

Example:
    To start the server (from the mcpskills directory):
    ```
    python ./server.py
    ```

Install into claude_desktop_config.json with:
$ mcp install ./server.py

Run for debugging with:
$ LOGLEVEL=DEBUG mcp dev ./server.py

Run for production with (or just use in Claude Desktop):
$ mcp run ./server.py

Note: Use ./server.py to explicitly run this server in the mcpskills directory

Additional complementary MCP servers:
- yahoo-finance-mcp: https://github.com/Alex2Yang97/yahoo-finance-mcp.git
- alphavantage: https://github.com/calvernaz/alphavantage.git
- fmp-mcp-server: https://github.com/cdtait/fmp-mcp-server
- wikipedia: pip install wikipedia-mcp
- brave-search: npm install -g @modelcontextprotocol/server-brave-search
- fetch: pip install mcp-server-fetch
- perplexity: https://github.com/ppl-ai/modelcontextprotocol/tree/main
- filesystem: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
"""
import os
import re
import random
import json
import sqlite3
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import dotenv
import numpy as np
import pandas as pd
from pydantic import Field
from mcp.server.fastmcp import FastMCP

import sec_parser as sp
from sec_downloader import Downloader

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import yfinance as yf
from mcp.server.fastmcp import FastMCP, Image as MCPImage

import aiohttp
import talib


import openbb
from openbb import obb
from openbb_core.app.model.obbject import OBBject

# Configuration constants
DEFAULT_LOOKBACK_DAYS = 365

# Technical indicator parameters
SMA_SHORT_PERIOD = 20
SMA_MEDIUM_PERIOD = 50
SMA_LONG_PERIOD = 200
ATR_PERIOD = 14
ADR_PERIOD = 20
RSI_PERIOD = 14
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

# Database configuration
SCRIPT_DIR = Path(__file__).parent.absolute()
BLOTTER_DB_PATH = SCRIPT_DIR / "blotter.db"


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize stock symbol.

    Validates that the symbol matches expected format and prevents
    path traversal or injection attacks.

    Args:
        symbol: Stock symbol to validate

    Returns:
        Uppercase validated symbol

    Raises:
        ValueError: If symbol format is invalid or contains dangerous characters
    """
    if not isinstance(symbol, str):
        raise ValueError("Symbol must be a string")

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Symbol cannot be empty")

    # Stock symbols: 1-5 uppercase letters, optionally with . or - for special cases
    if not re.match(r'^[A-Z]{1,5}([.-][A-Z]{1,2})?$', symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")

    # Additional check: prevent path traversal
    if '..' in symbol or '/' in symbol or '\\' in symbol:
        raise ValueError(f"Symbol contains invalid characters: {symbol}")

    return symbol


class MarketData:
    """
    Handles all market data fetching operations using Tiingo API.

    Attributes:
        api_key: Tiingo API key loaded from environment
        headers: HTTP headers for Tiingo API requests
    """

    def __init__(self) -> None:
        """
        Initialize MarketData with Tiingo API credentials.

        Raises:
            ValueError: If TIINGO_API_KEY environment variable is not set
        """
        self.api_key = os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY not found in environment")

        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}"
        }

    async def get_historical_data(
        self,
        symbol: str,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ) -> pd.DataFrame:
        """
        Fetch historical daily data for a given symbol.

        Args:
            symbol (str): The stock symbol to fetch data for.
            lookback_days (int): Number of days to look back from today.

        Returns:
            pd.DataFrame: DataFrame containing historical market data.

        Raises:
            ValueError: If the symbol is invalid or no data is returned.
            Exception: For other unexpected issues during the fetch operation.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        url = (
            f"https://api.tiingo.com/tiingo/daily/{symbol}/prices?"
            f'startDate={start_date.strftime("%Y-%m-%d")}&'
            f'endDate={end_date.strftime("%Y-%m-%d")}'
        )

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 404:
                        raise ValueError(f"Symbol not found: {symbol}")
                    response.raise_for_status()
                    data = await response.json()

            if not data:
                raise ValueError(f"No data returned for {symbol}")

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            df[["open", "high", "low", "close"]] = df[[
                "adjOpen", "adjHigh", "adjLow", "adjClose"]].round(2)
            df["volume"] = df["adjVolume"].astype(int)
            df["symbol"] = symbol.upper()

            return df

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Network error while fetching data for {symbol}: {e}")
        except ValueError as ve:
            raise ve  # Propagate value errors (symbol issues, no data, etc.)
        except Exception as e:
            raise Exception(
                f"Unexpected error fetching data for {symbol}: {e}")


class TechnicalAnalysis:
    """
    Technical analysis toolkit using TA-Lib for improved performance.

    Provides methods to calculate common technical indicators including
    moving averages, volatility measures, and momentum oscillators.
    """

    @staticmethod
    def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add a core set of technical indicators using TA-Lib.

        Calculates and adds the following indicators to the DataFrame:
        - Simple Moving Averages (20, 50, 200 periods)
        - Average True Range (ATR)
        - Average Daily Range Percentage (ADRP)
        - Average Volume
        - Relative Strength Index (RSI)
        - MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with columns: high, low, close, volume

        Returns:
            DataFrame with additional technical indicator columns

        Raises:
            KeyError: If required columns are missing from input DataFrame
            ValueError: If indicator calculation fails
        """
        try:
            # Convert to numpy arrays for TA-Lib (required format)
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            volume = df["volume"].values

            # Adding trend indicators (Simple Moving Averages)
            df["sma_20"] = talib.SMA(close, timeperiod=SMA_SHORT_PERIOD)
            df["sma_50"] = talib.SMA(close, timeperiod=SMA_MEDIUM_PERIOD)
            df["sma_200"] = talib.SMA(close, timeperiod=SMA_LONG_PERIOD)

            # Adding volatility indicators
            df["atr"] = talib.ATR(high, low, close, timeperiod=ATR_PERIOD)

            # Calculate Average Daily Range Percentage manually
            daily_range = df["high"] - df["low"]
            adr = daily_range.rolling(window=ADR_PERIOD).mean()
            df["adrp"] = (adr / df["close"]) * 100

            # Average volume (20-day)
            df["avg_20d_vol"] = df["volume"].rolling(window=ADR_PERIOD).mean()

            # Adding momentum indicators
            df["rsi"] = talib.RSI(close, timeperiod=RSI_PERIOD)

            # MACD indicator
            macd, macd_signal, macd_hist = talib.MACD(
                close,
                fastperiod=MACD_FAST_PERIOD,
                slowperiod=MACD_SLOW_PERIOD,
                signalperiod=MACD_SIGNAL_PERIOD
            )
            df["macd"] = macd
            df["macd_signal"] = macd_signal
            df["macd_histogram"] = macd_hist

            return df

        except KeyError as e:
            raise KeyError(f"Missing column in input DataFrame: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error calculating indicators: {str(e)}")

    @staticmethod
    def check_trend_status(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze the current trend status based on technical indicators.

        Examines the most recent data point to determine:
        - Price position relative to moving averages
        - Moving average crossovers (bullish/bearish)
        - RSI momentum
        - MACD trend direction

        Args:
            df: DataFrame with technical indicators already calculated

        Returns:
            Dictionary containing trend analysis with keys:
                - above_20sma, above_50sma, above_200sma: Price vs MA positions
                - 20_50_bullish, 50_200_bullish: MA crossover signals
                - rsi: Current RSI value
                - macd_bullish: MACD signal direction

        Raises:
            ValueError: If DataFrame is empty
        """
        if df.empty:
            raise ValueError(
                "DataFrame is empty. Ensure it contains valid data.")

        latest = df.iloc[-1]

        # Handle potential NaN values
        macd_bullish = False
        if not pd.isna(latest["macd"]) and not pd.isna(latest["macd_signal"]):
            macd_bullish = latest["macd"] > latest["macd_signal"]

        return {
            "above_20sma": latest["close"] > latest["sma_20"] if not pd.isna(latest["sma_20"]) else False,
            "above_50sma": latest["close"] > latest["sma_50"] if not pd.isna(latest["sma_50"]) else False,
            "above_200sma": latest["close"] > latest["sma_200"] if not pd.isna(latest["sma_200"]) else False,
            "20_50_bullish": latest["sma_20"] > latest["sma_50"] if not pd.isna(latest["sma_20"]) and not pd.isna(latest["sma_50"]) else False,
            "50_200_bullish": latest["sma_50"] > latest["sma_200"] if not pd.isna(latest["sma_50"]) and not pd.isna(latest["sma_200"]) else False,
            "rsi": latest["rsi"] if not pd.isna(latest["rsi"]) else 0,
            "macd_bullish": macd_bullish,
        }


# Load environment variables
dotenv.load_dotenv()

# Change working directory to the directory where this script is located
os.chdir(SCRIPT_DIR)

# Configure logging
log_dir = SCRIPT_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
today = datetime.today()
log_file = log_dir / f"{today.strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    filename=log_file,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)
logger.info("Starting in directory: %s", os.getcwd())


def create_or_get_temp_dir(symbol: str) -> str:
    """
    Create or retrieve temporary directory for symbol-specific data storage.

    Creates a directory named {SYMBOL}-{YYYY-MM-DD} in the current directory
    using today's date and the provided stock symbol (uppercase).

    Args:
        symbol: Stock symbol (will be converted to uppercase)

    Returns:
        Absolute path to the created or existing directory

    Note:
        If the directory already exists, returns the existing path.
        Directory is created in the script's working directory.
    """
    today = datetime.today()
    dir_name = f"{symbol.upper()}-{today.strftime('%Y-%m-%d')}"
    full_path = os.path.abspath(dir_name)
    if not os.path.exists(full_path):
        logger.info("Creating directory: %s", full_path)
        os.makedirs(full_path)
    else:
        logger.info("Directory already exists: %s", full_path)
    return full_path


##################################################
# Test data generation for blotter database
##################################################

# Company and pricing info for generating test trades
COMPANIES: Dict[str, Tuple[str, float]] = {
    "MSFT": ("Microsoft Corp.", 330),
    "NVDA": ("Nvidia Corp.", 850),
    "AAPL": ("Apple, Inc.", 190),
    "META": ("Meta Platforms, Inc.", 470),
    "GOOG": ("Alphabet Inc.", 135),
    "AMZN": ("Amazon.com, Inc.", 185),
    "AVGO": ("Broadcom Inc.", 1800),
    "TSM": ("Taiwan Semiconductor Mfg.", 150),
    "TSLA": ("Tesla, Inc.", 150)
}


def random_weekday_date(year: int = 2025) -> str:
    """
    Generate a random weekday date in the specified year.

    Args:
        year: Year for which to generate date (default: 2025)

    Returns:
        Date string in YYYY-MM-DD format representing a weekday
    """
    while True:
        d = datetime(year, 1, 1) + timedelta(days=random.randint(0, 364))
        if d.weekday() < 5:  # Mon-Fri
            return d.strftime("%Y-%m-%d")


def generate_fake_trade() -> Tuple[str, str, str, str, int, float]:
    """
    Generate a single fake trade record for testing.

    Returns:
        Tuple containing (date, symbol, company, side, quantity, price)
        where:
            - date: Trade date in YYYY-MM-DD format
            - symbol: Stock ticker symbol
            - company: Company name
            - side: "BUY" or "SELL"
            - quantity: Number of shares
            - price: Price per share
    """
    symbol = random.choice(list(COMPANIES.keys()))
    company, base_price = COMPANIES[symbol]
    date = random_weekday_date()
    price = round(random.gauss(mu=base_price, sigma=base_price * 0.05), 2)
    total_value = random.randint(10_000, 100_000)
    quantity = max(1, int(total_value / price))
    side = random.choice(["BUY", "SELL"])
    return (date, symbol, company, side, quantity, price)


def insert_fake_trades() -> None:
    """
    Initialize the blotter database with fake trade data.

    Creates a SQLite database with a blotter table and populates it
    with 1000 randomly generated trade records for testing purposes.

    Note:
        This function drops and recreates the blotter table,
        destroying any existing data.
    """
    # Use context manager to ensure proper resource cleanup
    with sqlite3.connect(BLOTTER_DB_PATH) as conn:
        cur = conn.cursor()

        # Create table
        cur.execute("DROP TABLE IF EXISTS blotter")
        cur.execute("""
        CREATE TABLE blotter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            symbol TEXT,
            company TEXT,
            side TEXT,
            quantity INTEGER,
            price REAL
        )
        """)

        # Insert fake trades
        trades = [generate_fake_trade() for _ in range(1000)]
        cur.executemany("""
        INSERT INTO blotter (date, symbol, company, side, quantity, price)
        VALUES (?, ?, ?, ?, ?, ?)
        """, trades)

        # Commit is automatic with context manager on success


# Initialize MCP server
# needed for tool definitions below
mcp = FastMCP("stock-symbol-server")


@mcp.tool()
def get_trades_for_symbol(
    symbol: str = Field(description="The stock symbol to query trades for")
) -> str:
    """
    Retrieve all trades for a given symbol from the blotter database.

    Queries the blotter SQLite database for all trade records matching
    the specified stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string containing array of trade records with fields:
        id, date, symbol, company, side, quantity, price

    Raises:
        ValueError: If symbol format is invalid
        sqlite3.DatabaseError: If database query fails
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    logger.info("Fetching trades for symbol: %s", symbol)

    try:
        with sqlite3.connect(BLOTTER_DB_PATH) as conn:
            df = pd.read_sql_query(
                "SELECT * FROM blotter WHERE symbol = ?",
                conn,
                params=(symbol,)
            )
            logger.info("Found %d trades for symbol %s", len(df), symbol)
        return df.to_json(orient='records')
    except sqlite3.DatabaseError as e:
        logger.error("Database error fetching trades for %s: %s", symbol, e)
        raise
    except Exception as e:
        logger.exception("Unexpected error fetching trades for %s", symbol)
        raise


@mcp.tool()
def fetch_10k_item1(
    symbol: str = Field(description="The stock symbol whose 10-K item 1 is requested")
) -> str:
    """
    Get Item 1 (Business Description) of the latest 10-K annual report.

    Retrieves and parses the most recent 10-K filing from SEC EDGAR,
    extracting Item 1 which contains the business description.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Text content of Item 1 from the 10-K filing, or empty string if not found

    Raises:
        ValueError: If symbol format is invalid or SEC credentials not configured
        ConnectionError: If SEC API request fails
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    temp_dir = create_or_get_temp_dir(symbol)
    item_text = ""

    # Validate SEC credentials
    sec_firm = os.getenv("SEC_FIRM")
    sec_user = os.getenv("SEC_USER")
    if not sec_firm or not sec_user:
        raise ValueError("SEC_FIRM and SEC_USER environment variables must be set")

    try:
        logger.info("Getting 10-K Item 1 for %s", symbol)
        dl = Downloader(sec_firm, sec_user)
        html = dl.get_filing_html(ticker=symbol, form="10-K")
        logger.info("HTML length: %d characters", len(html))

        elements = sp.Edgar10QParser().parse(html)
        tree = sp.TreeBuilder().build(elements)

        # Look for "ITEM 1" section
        item = "1"
        sections = [
            n for n in tree.nodes
            if re.match(r"^ITEM\s+" + item, n.text.strip().upper())
        ]
        logger.info("Sections found: %d", len(sections))

        if len(sections) == 0:
            logger.warning("No Item 1 section found in 10-K for %s", symbol)
            return ""

        item_node = sections[0]
        item_text = item_node.text + "\n\n" + \
            "\n".join([n.text for n in item_node.get_descendants()])
        logger.info("Item text: %d characters", len(item_text))

        # Save to file
        with open(os.path.join(temp_dir, "10k_item_1.txt"), "w", encoding="utf-8") as f:
            f.write(item_text)

    except ConnectionError as e:
        logger.error("Network error fetching 10-K for %s: %s", symbol, e)
        raise
    except ValueError as e:
        logger.error("Parsing error for %s: %s", symbol, e)
        raise
    except Exception as e:
        logger.exception("Unexpected error fetching 10-K for %s", symbol)
        raise

    return item_text


@mcp.tool()
def make_stock_chart(
    symbol: str = Field(description="The stock symbol to chart")
) -> MCPImage:
    """
    Create a comprehensive stock chart with technical indicators.

    Generates a multi-panel Plotly chart showing:
    - Weekly candlestick price chart with 13 and 52-week moving averages
    - Volume bars (color-coded by price direction)
    - Relative strength vs S&P 500

    Chart is saved to temp directory and returned as inline image.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        MCPImage containing PNG chart data

    Raises:
        ValueError: If symbol format is invalid or data unavailable
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    temp_dir = create_or_get_temp_dir(symbol)

    # Download weekly data
    symbol_df = yf.download(symbol, interval="1wk", period="4y")
    symbol_df.columns = [col[0] if col[1] == symbol else col[0]
                         for col in symbol_df.columns]
    spx_df = yf.download("^GSPC", interval="1wk", period="4y")
    spx_df.columns = [col[0] if col[1] == '^GSPC' else col[0]
                      for col in spx_df.columns]

    # Compute moving averages
    symbol_df['MA13'] = symbol_df['Close'].rolling(window=13).mean()
    symbol_df['MA52'] = symbol_df['Close'].rolling(window=52).mean()

    # Compute relative strength vs SPX
    relative = symbol_df['Close'] / spx_df['Close']
    symbol_df['Rel_SPX'] = relative

    # Create figure with secondary y-axis in the first row
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.02,
        specs=[[{"secondary_y": True}], [{}]],
        subplot_titles=[None, None]  # Remove default titles for cleaner look
    )

    # --- Row 1: Price Candlesticks & MAs (primary y-axis) ---
    fig.add_trace(go.Candlestick(
        x=symbol_df.index,
        open=symbol_df['Open'],
        high=symbol_df['High'],
        low=symbol_df['Low'],
        close=symbol_df['Close'],
        name=symbol,
        increasing_line_color='#2E8B57',  # Sea green for up candles
        decreasing_line_color='#DC143C',  # Crimson for down candles
        increasing_fillcolor='#2E8B57',
        decreasing_fillcolor='#DC143C',
        line=dict(width=1)
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['MA13'],
        mode='lines',
        name='MA(13)',
        line=dict(color='#4169E1', width=2),  # Royal blue
        opacity=0.8
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['MA52'],
        mode='lines',
        name='MA(52)',
        line=dict(color='#FF6347', width=2),  # Tomato red
        opacity=0.8
    ), row=1, col=1, secondary_y=False)

    # --- Row 1: Volume on right axis (secondary y-axis) ---
    # Color volume bars based on price direction
    volume_colors = ['#90EE90' if close >= open else '#FFB6C1'
                     for close, open in zip(symbol_df['Close'], symbol_df['Open'])]

    fig.add_trace(go.Bar(
        x=symbol_df.index,
        y=symbol_df['Volume'],
        name='Volume',
        marker_color=volume_colors,
        opacity=0.6,
        showlegend=False
    ), row=1, col=1, secondary_y=True)

    # --- Row 2: Relative to SPX ---
    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['Rel_SPX'],
        name=f'{symbol} / SPX',
        mode='lines',
        line=dict(color='#2F4F4F', width=2),  # Dark slate gray
        fill='tonexty',
        fillcolor='rgba(47, 79, 79, 0.1)'
    ), row=2, col=1)

    # Get latest price for title
    latest_price = symbol_df['Close'].iloc[-1]
    latest_change = symbol_df['Close'].iloc[-1] - symbol_df['Close'].iloc[-2]
    latest_change_pct = (latest_change / symbol_df['Close'].iloc[-2]) * 100

    # Enhanced layout with gradient background and professional styling
    fig.update_layout(
        title={
            'text': f'{symbol} - ${latest_price:.2f} ({latest_change:+.2f}, {latest_change_pct:+.1f}%)',
            'x': 0.02,
            'y': 0.98,
            'xanchor': 'left',
            'yanchor': 'top',
            'font': {'size': 16, 'color': '#2F4F4F', 'family': 'Arial, sans-serif'}
        },
        height=600,
        width=900,

        # Gradient background
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',

        # Grid styling
        xaxis=dict(
            rangeslider_visible=False,
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.3)',
            showline=True,
            linewidth=1,
            linecolor='#D3D3D3',
            tickfont=dict(size=10, color='#696969')
        ),

        # Legend styling
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#D3D3D3',
            borderwidth=1,
            font=dict(size=10)
        ),

        # Margins
        margin=dict(l=60, r=80, t=80, b=40),

        # Remove subplot titles spacing
        annotations=[]
    )

    # Style the y-axes
    fig.update_yaxes(
        title_text="Price ($)",
        row=1, col=1, secondary_y=False,
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.3)',
        showline=True,
        linewidth=1,
        linecolor='#D3D3D3',
        tickfont=dict(size=10, color='#696969'),
        title_font=dict(size=12, color='#2F4F4F')
    )

    # Calculate volume range and set max to show volume in bottom 1/3 of chart
    max_volume = symbol_df['Volume'].max()
    volume_range = [0, max_volume * 3]  # Scale so max volume is at 1/3 height

    fig.update_yaxes(
        title_text="Volume",
        row=1, col=1, secondary_y=True,
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='#D3D3D3',
        tickfont=dict(size=10, color='#696969'),
        title_font=dict(size=12, color='#2F4F4F'),
        side='right',
        range=volume_range,
        showticklabels=True,
        tickmode='auto'
    )

    fig.update_yaxes(
        title_text=f"{symbol} / SPX Ratio",
        row=2, col=1,
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.3)',
        showline=True,
        linewidth=1,
        linecolor='#D3D3D3',
        tickfont=dict(size=10, color='#696969'),
        title_font=dict(size=12, color='#2F4F4F')
    )

    # Style the x-axes
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.3)',
        showline=True,
        linewidth=1,
        linecolor='#D3D3D3',
        tickfont=dict(size=10, color='#696969')
    )

    # Add gradient background using shapes
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=0, y0=0, x1=1, y1=1,
        fillcolor="rgba(240, 248, 255, 0.8)",  # Alice blue with transparency
        layer="below",
        line_width=0,
    )

    # Convert the plot to a PNG image and return as FastMCP Image
    # Use unique filename to prevent race conditions in concurrent requests
    unique_id = uuid.uuid4().hex[:8]
    dt = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = os.path.join(temp_dir, f"plotly_chart_{dt}_{unique_id}.png")
    fig.write_image(filename, width=800, height=600, scale=2)

    img_bytes = pio.to_image(fig, format="png", width=800, height=600)

    return MCPImage(data=img_bytes, format="png")


@mcp.tool()
async def technical_analysis(
    symbol: str = Field(description="The stock symbol to perform technical analysis on")
) -> str:
    """
    Perform comprehensive technical analysis on a stock.

    Calculates technical indicators and generates a formatted analysis report
    covering trend, momentum, and volatility metrics. Report is saved to
    temp directory and returned as text.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Formatted technical analysis report as string

    Raises:
        ValueError: If symbol format is invalid or data unavailable
        ConnectionError: If market data API request fails
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    temp_dir = create_or_get_temp_dir(symbol)

    # Perform analysis workflow
    market_data = MarketData()
    tech_analysis = TechnicalAnalysis()

    df = await market_data.get_historical_data(symbol)
    df = tech_analysis.add_core_indicators(df)
    trend = tech_analysis.check_trend_status(df)

    analysis = f"""
Technical Analysis for {symbol}:

Trend Analysis:
- Above 20 SMA: {'✅' if trend['above_20sma'] else '❌'}
- Above 50 SMA: {'✅' if trend['above_50sma'] else '❌'}
- Above 200 SMA: {'✅' if trend['above_200sma'] else '❌'}
- 20/50 SMA Bullish Cross: {'✅' if trend['20_50_bullish'] else '❌'}
- 50/200 SMA Bullish Cross: {'✅' if trend['50_200_bullish'] else '❌'}

Momentum:
- RSI (14): {trend['rsi']:.2f}
- MACD Bullish: {'✅' if trend['macd_bullish'] else '❌'}

Latest Price: ${df['close'].iloc[-1]:.2f}
Average True Range (14): {df['atr'].iloc[-1]:.2f}
Average Daily Range Percentage: {df['adrp'].iloc[-1]:.2f}%
Average Volume (20D): {df['avg_20d_vol'].iloc[-1]:,.0f}
"""
    with open(os.path.join(temp_dir, "technical_analysis.txt"), "w", encoding="utf-8") as f:
        f.write(analysis)

    return analysis


def get_financial_ratios(symbol: str) -> pd.DataFrame:
    """
    Retrieve comprehensive financial ratios for a given symbol using yfinance.

    Fetches and organizes financial metrics into categories including
    valuation, financial highlights, profitability, liquidity, and
    per-share data.

    Args:
        symbol: Stock ticker symbol (should be validated before calling)

    Returns:
        DataFrame with columns: Category, Metric, {symbol}
        containing ratios organized by category

    Raises:
        ValueError: If symbol is invalid or data unavailable
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    if not info:
        raise ValueError(f"No data available for symbol: {symbol}")

    # Organize ratios by category
    valuation_ratios = {
        'Trailing P/E': info.get('trailingPE'),
        'Forward P/E': info.get('forwardPE'),
        'PEG Ratio': info.get('pegRatio'),
        'Price/Sales (ttm)': info.get('priceToSalesTrailing12Months'),
        'Price/Book': info.get('priceToBook'),
        'Enterprise Value/Revenue': info.get('enterpriseToRevenue'),
        'Enterprise Value/EBITDA': info.get('enterpriseToEbitda'),
    }

    financial_highlights = {
        'Market Cap': info.get('marketCap'),
        'Enterprise Value': info.get('enterpriseValue'),
        'Revenue (ttm)': info.get('totalRevenue'),
        'Gross Profit (ttm)': info.get('grossProfits'),
        'EBITDA': info.get('ebitda'),
        'Net Income (ttm)': info.get('netIncomeToCommon'),
    }

    profitability_ratios = {
        'Profit Margin': info.get('profitMargins'),
        'Operating Margin': info.get('operatingMargins'),
        'Gross Margin': info.get('grossMargins'),
        'EBITDA Margin': info.get('ebitdaMargins'),
        'Return on Assets': info.get('returnOnAssets'),
        'Return on Equity': info.get('returnOnEquity'),
    }

    liquidity_ratios = {
        'Current Ratio': info.get('currentRatio'),
        'Quick Ratio': info.get('quickRatio'),
        'Total Cash': info.get('totalCash'),
        'Total Debt': info.get('totalDebt'),
        'Debt/Equity': info.get('debtToEquity'),
    }

    per_share_data = {
        'Earnings Per Share (ttm)': info.get('trailingEps'),
        'Book Value Per Share': info.get('bookValue'),
        'Revenue Per Share': info.get('revenuePerShare'),
        'Operating Cash Flow Per Share': (
            info.get('operatingCashflow', 0) / info['sharesOutstanding']
            if info.get('sharesOutstanding') and info['sharesOutstanding'] > 0
            else None
        ),
    }

    # Combine all categories
    all_ratios = {
        **valuation_ratios,
        **financial_highlights,
        **profitability_ratios,
        **liquidity_ratios,
        **per_share_data
    }

    # Create DataFrame
    df = pd.DataFrame(list(all_ratios.items()), columns=['Metric', symbol])
    df['Category'] = (
        ['Valuation'] * len(valuation_ratios) +
        ['Financial Highlights'] * len(financial_highlights) +
        ['Profitability'] * len(profitability_ratios) +
        ['Liquidity'] * len(liquidity_ratios) +
        ['Per Share'] * len(per_share_data)
    )
    return df[["Category", "Metric", symbol]]


@mcp.tool()
def get_fundamental_ratios(
    symbol: str = Field(description="The stock symbol to get fundamentals on")
) -> str:
    """
    Get comprehensive fundamental ratios compared to peer companies.

    Retrieves financial ratios for the specified symbol and its industry
    peers, presenting them in a side-by-side comparison table.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Markdown-formatted table comparing ratios across symbol and peers

    Raises:
        ValueError: If symbol format is invalid or OPENBB_PAT not configured
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    temp_dir = create_or_get_temp_dir(symbol)

    # Validate OpenBB credentials
    openbb_pat = os.getenv('OPENBB_PAT')
    if not openbb_pat:
        raise ValueError("OPENBB_PAT environment variable not set")
    obb.user.credentials.openbb_pat = openbb_pat

    # Get ratios for primary symbol
    symbol_df = get_financial_ratios(symbol)

    # Get peers list
    obj = obb.equity.compare.peers(symbol=symbol, provider='fmp')
    peers_df = obj.to_df()
    peers_list = peers_df['symbol'].to_list()

    # Get ratios for each peer (only keep last column of data)
    peers_dflist = [get_financial_ratios(p).iloc[:, 2] for p in peers_list]

    # Concatenate original table with peer data
    df = pd.concat([symbol_df] + peers_dflist, axis=1)
    md_str = df.to_markdown()

    # Save to file
    with open(os.path.join(temp_dir, "peers_ratios.md"), "w", encoding="utf-8") as f:
        f.write(md_str)

    return md_str


@mcp.tool()
def get_peers(
    symbol: str = Field(description="The stock symbol to get peers for")
) -> str:
    """
    Get a list of peer companies for a given symbol.

    Retrieves industry peer companies using OpenBB's peer comparison
    functionality powered by Financial Modeling Prep data.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        JSON string containing peer company data

    Raises:
        ValueError: If symbol format is invalid or OPENBB_PAT not configured
    """
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)
    temp_dir = create_or_get_temp_dir(symbol)

    # Validate OpenBB credentials
    openbb_pat = os.getenv('OPENBB_PAT')
    if not openbb_pat:
        raise ValueError("OPENBB_PAT environment variable not set")
    obb.user.credentials.openbb_pat = openbb_pat

    # Get peers data
    obj = obb.equity.compare.peers(symbol=symbol, provider='fmp')
    json_str = json.dumps(obj.to_dict())

    # Save to file
    with open(os.path.join(temp_dir, "peers.json"), "w", encoding="utf-8") as f:
        f.write(json_str)

    return json_str


@mcp.tool()
def get_peers_ratios(
    symbol: str = Field(description="The stock symbol to get peers ratios on")
) -> str:
    """
    Get a table of comparable ratios of peers for a given symbol.

    Note: This tool provides identical functionality to get_fundamental_ratios.
    Consider using get_fundamental_ratios instead.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")

    Returns:
        Markdown-formatted table comparing ratios across symbol and peers

    Raises:
        ValueError: If symbol format is invalid or OPENBB_PAT not configured
    """
    # This is a duplicate of get_fundamental_ratios - delegate to it
    return get_fundamental_ratios(symbol)


def main() -> None:
    """
    Main entry point for the MCP server.

    Initializes and runs the FastMCP server using stdio transport,
    making it available for MCP clients like Claude Desktop.

    The server provides tools for:
    - Stock market data and technical analysis
    - SEC filing retrieval
    - Financial ratio analysis
    - Peer company comparisons
    - Stock chart generation
    """
    logger.info("MCP Server - Stock Research")
    logger.info("==========================")

    # Run the server using stdio transport
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
