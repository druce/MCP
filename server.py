"""MCP (Model Context Protocol) Server Implementation.

This module implements a simple MCP server using FastMCP, providing:
- Basic arithmetic operations (e.g., addition)
- Dynamic resource generation (e.g., personalized greetings)

The server follows the Model Context Protocol specification as defined at:
https://modelcontextprotocol.io/

Example:
    To start the server:
    ```
    python server.py
    ```

    Then interact with the server using the MCP client or via HTTP requests:
    - Tool endpoint: POST http://localhost:8000/tools/add
    - Resource endpoint: GET http://localhost:8000/resources/greeting/World

Install into claude_desktop_config.json with:
$ mcp install server.py

Run for debugging with:
$ LOGLEVEL=DEBUG mcp dev server.py

Run for production with (or just use in Claude Desktop):
$ mcp run server.py
"""
# pylint: disable=broad-except
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import secrets
import time
import re
import os
import logging
# import sys
import io
from typing import Dict, List, Optional, AsyncIterator
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import sec_parser as sp
from sec_downloader import Downloader
from playwright.async_api import (
    async_playwright,
    BrowserContext as AsyncBrowserContext,
    Page as AsyncPage
)
from plotly.subplots import make_subplots
from PIL import Image as PILImage
import yfinance as yf
from mcp.server.fastmcp import FastMCP, Image as MCPImage
import yaml
import plotly.io as pio
import plotly.graph_objects as go
import httpx
import dotenv

from typing_extensions import Annotated

from openbb import obb

from scrape import get_browser, normalize_html
from technical_analysis import MarketData, TechnicalAnalysis

# import importlib
# from mcp.types import Resource
# from mcp.server import Server

# from pydantic import Field  # BaseModel, DirectoryPath

# Load environment variables
dotenv.load_dotenv()

SOURCES = "sources.yaml"

# Change working directory to the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

logger = logging.getLogger(__name__)
logger.info("Starting in directory: %s", os.getcwd())


@dataclass
class SourceConfig:
    """Configuration for a data source used in web scraping.

    Attributes:
        name (str): The name of the data source.
        description (str): A description of the data source, can be used for a tool description.
        url_template (str): Template string for constructing the source URL.
        exchange_mappings (str, optional): Mapping of exchange names to their corresponding values in the URL template.
        required_params (List[str]): List of required parameters for the URL template.
        wait_strategy (str, optional): Page load strategy (e.g., 'load', 'domcontentloaded').
            Defaults to "load".
        rate_limit (float, optional): Minimum delay between requests in seconds.
            Defaults to 2.0.
        priority (int, optional): Priority of the source (lower number = higher priority).
            Defaults to 2.
        data_type (str, optional): Type of data provided by the source.
            Defaults to "general".
    """
    name: str
    description: str
    url_template: str
    required_params: List[str]
    exchange_mappings: Optional[str] = None
    wait_strategy: str = "load"
    extract_mode: str = "text"
    rate_limit: float = 2.0
    data_type: str = "general"
    exclude: Optional[List[str]] = None
    include: Optional[List[str]] = None


def get_path_from_url(url):
    """
    Extracts the path following the top-level domain name from a URL.

    :param url: The URL string.
    :return: The path component of the URL.
    """
    parsed_url = urlparse(url)
    return parsed_url.path


def trimmed_href(link):
    """
    Trims everything in the link after a question mark such as a session ID.

    :param link: The input string or bs4 link.
    :return: The trimmed string.
    """
    # Find the position of the question mark
    if isinstance(link, str):
        s = link
    else:
        s = link.get("href")
    if s:
        question_mark_index = s.find("?")

        # If a question mark is found, trim the string up to that point
        if question_mark_index != -1:
            return s[:question_mark_index]
        else:
            # Return the original string if no question mark is found
            return s
    else:
        return s

# could use mcp-server-playwright - making our own playwright browsercontext is probably not needed
# assuming we can point that server to a profile with saved credentials, or provide credentials in the tool call
# mcp-server-readability - Combines fetching with content extraction


class StockDataExtractor:
    """Stock data extractor for web scraping."""

    def __init__(self, browser_context: AsyncBrowserContext,
                 sources: Dict[str, SourceConfig],
                 exchanges: Dict[str, Dict[str, str]]
                 ):
        self.browser_context = browser_context
        self.sources = sources
        self.exchanges = exchanges
        self.page_pool: List[AsyncPage] = []
        self.last_request_time: Dict[str, float] = {}

    async def get_or_create_page(self) -> AsyncPage:
        """Get a page from the pool or create a new one."""
        if self.page_pool:
            return self.page_pool.pop()
        if not hasattr(self, 'browser_context') or self.browser_context is None:
            raise RuntimeError(
                "Browser is not initialized. Call browser_lifespan() first.")
        return await self.browser_context.new_page()

    async def return_page(self, page: AsyncPage):
        """Return a page to the pool for reuse."""
        try:
            # Clear the page state
            await page.goto("about:blank")
            await page.evaluate(
                "() => { localStorage.clear(); sessionStorage.clear(); }")
            self.page_pool.append(page)
        except Exception as e:
            print(f"Error returning page to pool: {str(e)}")
            # If cleaning fails, close the page
            await page.close()

    def respect_rate_limit(self, source_key: str, rate_limit: float):
        """Ensure we respect rate limits for each source."""
        now = time.time()
        last_request = self.last_request_time.get(source_key, 0)
        time_since_last = now - last_request

        if time_since_last < rate_limit:
            sleep_time = rate_limit - time_since_last
            time.sleep(sleep_time)

        self.last_request_time[source_key] = time.time()

    def map_exchange(self, source_key: str, exchange: str) -> str:
        """Map exchange codes for specific platforms."""
        logger.info("Applying exchange mappings for %s", source_key)
        mappings = self.exchanges.get(source_key, {})
        return mappings.get(exchange, exchange)

    async def fetch_url(self, url: str, wait_strategy: str = 'networkidle', extract_mode='text', include=[], exclude=[]) -> dict:
        """Fetch a page using the browser context.
        text = normalized text
        raw_html = raw html
        links = markdown of only links and titles"""
        # Get a browser page using the browser context
        try:
            page = await self.get_or_create_page()

            # Navigate to the URL with the specified wait strategy
            response = await page.goto(url, wait_until=wait_strategy)
            if not response or response.status != 200:
                return {
                    "url": url,
                    "status": "error",
                    "message": f"Failed to load page (status: {response.status if response else 'unknown'})",
                }

            # Wait for the page to be fully loaded
            await page.wait_for_load_state(wait_strategy)

            content = await page.content()

            if extract_mode == 'text':
                content = self.normalize_page_content(content)
            elif extract_mode == 'raw_html':
                pass
            elif extract_mode == 'links':
                soup = BeautifulSoup(content, 'html.parser')
                links = soup.find_all("a")
                logger.info("found %d raw links", len(links))
                # drop empty text
                links = [link for link in links if link.get_text(strip=True)]
                # drop some ArsTechnica links that are just the number of comments and dupe the primary link
                links = [link for link in links if not re.match(
                    "^(\d+)$", link.get_text(strip=True))]

                # convert relative links to absolute links using base URL if present
                base_tag = soup.find('base')
                base_url = base_tag.get('href') if base_tag else url
                for link in links:
                    link["href"] = urljoin(base_url, link.get('href', ""))

                # drop empty url path, i.e. url = toplevel domain
                links = [link for link in links if len(
                    get_path_from_url(trimmed_href(link))) > 1]
                # drop anything that is not http, like javascript: or mailto:
                links = [link for link in links if link.get(
                    "href") and link.get("href").startswith("http")]
                # remove duplicate links
                links = list(
                    {link.get("href"): link for link in links}.values())

                logger.info("found %d links after filtering", len(links))
                logger.info("exclude: %s", exclude)
                logger.info("include: %s", include)
                if exclude:
                    for pattern in exclude:
                        # filter links by exclusion pattern
                        links = [
                            link
                            for link in links
                            if link.get("href") is not None and not re.match(pattern, link.get("href"))
                        ]

                logger.info("found %d links after exclude", len(links))
                if include:
                    for pattern in include:
                        new_links = []
                        for link in links:
                            href = link.get("href")
                            if href and re.match(pattern, href):
                                new_links.append(link)
                        links = new_links

                logger.info("found %d links after include", len(links))
                for link in links:
                    url = trimmed_href(link)
                    title = link.get_text(strip=True)
                    # skip some low quality links that don't have full headline, like link to a Twitter or Threads account
                    if len(title) <= 3:
                        continue
                # convert links to markdown
                links_markdown = [f"[{a.text}]({a['href']})" for a in links]
                content = '\n'.join(links_markdown)
            else:
                logger.error("invalid extract_mode %s", extract_mode)
                return {
                    "url": url,
                    "status": "error",
                    "message": "invalid extract_mode %s" % extract_mode,
                }

            return {
                "url": url,
                "status": "success",
                "content": content,
            }
        except Exception as e:
            logger.error("Error fetching page: %s", e)
            return {
                "url": url,
                "status": "error",
                "message": str(e),
            }
        finally:
            # Return the page to the pool
            await self.return_page(page)

    def normalize_page_content(self, content: str) -> str:
        """Normalize page content."""
        try:
            temp_file = Path(
                f"data/stock_page_{secrets.token_hex(20)}.html")
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_text(content, encoding='utf-8')
            # Normalize content
            content = normalize_html(temp_file)
            # Cleanup temp file
            temp_file.unlink()
            return content
        except Exception as e:
            logger.error("Failed to normalize page content: %s", e)
            return content

    async def fetch_source_content(
        self,
        source_key: str,
        symbol: str = None,
        company: str = None,
        exchange: str = None,
        maxlength: int = 999999,
        **kwargs
    ) -> dict:
        """
        Helper function to fetch and normalize content from any configured source.

        Args:
            source_key: The key of the source in sources.yaml
            symbol: The stock symbol to look up
            company: Optional company name (required for some sources)
            exchange: Optional exchange code (required for some sources)
            **kwargs: Additional parameters that might be needed for the URL template

        Returns:
            dict: Dictionary containing the URL, status, message, and normalized content
        """

        try:
            logger.info("Fetching content from %s", source_key)

            if source_key not in self.sources:
                raise ValueError(
                    f"Source '{source_key}' not found in configuration")

            source_config = self.sources[source_key]
            if hasattr(source_config, 'extract_mode') and source_config.extract_mode:
                extract_mode = source_config.extract_mode
            else:
                extract_mode = 'text'

            if hasattr(source_config, 'include') and source_config.include:
                include = source_config.include
            else:
                include = []

            if hasattr(source_config, 'exclude') and source_config.exclude:
                exclude = source_config.exclude
            else:
                exclude = []

            # Prepare template variables
            template_vars = {
                'symbol': symbol or '',
                'company': company or '',
                'exchange': exchange or '',
                **kwargs
            }

            # map exchange
            if hasattr(source_config, 'exchange_mappings') and exchange:
                template_vars['exchange'] = self.map_exchange(
                    source_key, exchange)
                logger.info("Exchange mapping found : %s",
                            template_vars['exchange'])

            # Format URL with template variables
            clean_dict = {k: v for k, v in template_vars.items()
                          if v is not None}
            required_params = getattr(source_config, 'required_params', [])
            if any(param not in clean_dict for param in required_params):
                raise ValueError(f"All required template variables ({required_params}) "
                                 f"were not found in {clean_dict}")
            url = source_config.url_template.format(**clean_dict)
            logger.info("URL: %s", url)
            logger.info("Extract mode: %s", extract_mode)

            extractor_response = await self.fetch_url(url, source_config.wait_strategy, extract_mode, include, exclude)

            if not extractor_response or extractor_response.get('status') != 'success':
                message = extractor_response.get(
                    'message') if extractor_response else "Failed to get page content"
                return {
                    "url": url,
                    "status": "error",
                    "message": message
                }

            content = extractor_response.get('content')

            return {
                "url": url,
                "status": "success",
                "message": f"Successfully loaded {source_config.name}",
                "content": content[:maxlength],
                "source": source_key
            }

        except Exception as e:
            return {
                "url": url if 'url' in locals() else None,
                "status": "error",
                "message": str(e),
                "source": source_key
            }


@dataclass
class AppContext:
    """App context for web scraping."""
    stock_data_extractor: StockDataExtractor = field(
        default_factory=StockDataExtractor)


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage app lifecycle with persistent data: browser, sources, exchanges.

    Args:
        _server: The MCP server instance (unused in this implementation)

    Yields:
        AppContext: The initialized app context
    """
    try:
        # Load configuration for AppContext
        logger.info("Loading configuration...")
        with open(SOURCES, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        sources = {}
        for key, source_data in config['sources'].items():
            sources[key] = SourceConfig(**source_data)
        logger.info("Successfully loaded %d sources", len(sources))

        exchange_mappings = config.get('exchange_mappings', {})
        for exchange_name in exchange_mappings:
            logger.info("Loaded exchange mapping for %s", exchange_name)

        # Initialize browser
        logger.info("Initializing global app context...")
        async with async_playwright() as playwright:
            browser = None
            try:
                logger.info("Launching global browser for scraping...")
                browser = await get_browser(playwright)
                logger.info("Browser launched")

                context = AppContext(
                    stock_data_extractor=StockDataExtractor(browser,
                                                            sources=sources,
                                                            exchanges=exchange_mappings
                                                            ))
                logger.info("Global app context created")
                # potentially add pages to the pool here
                yield context
            except Exception as e:
                logger.error(
                    "Error initializing browser: %s", str(e), exc_info=True)
                raise
            finally:
                # Cleanup
                if browser:
                    logger.info("Closing browser...")
                    await browser.close()
                    logger.info("Browser closed")
    except Exception as e:
        logger.error("Error in browser_lifespan: %s", str(e), exc_info=True)
        raise


def fn_get_10k_item_from_symbol(symbol, item="1"):
    """
    Get item 1 (or other number) of the latest 10-K annual report filing for a given symbol.

    Args:
        symbol (str): The symbol of the equity.
        item (str):   The item number to return.

    Returns:
        str: The item requested from the latest 10-K annual report filing, or None if not found.

    """

    item_text = ""
    try:
        logger.info("Getting 10-K Item 1 for %s", symbol)
        dl = Downloader(os.getenv("SEC_FIRM"), os.getenv("SEC_USER"))
        html = dl.get_filing_html(ticker=symbol, form="10-K")
        logger.info("HTML length: %d characters", len(html))
        elements = sp.Edgar10QParser().parse(html)
        tree = sp.TreeBuilder().build(elements)
        # look for e.g. "Item 1."
        # sections = [n for n in tree.nodes if re.match(r"^ITEM 1[A-Z]?\.", n.text.strip().upper())]
        sections = [n for n in tree.nodes if re.match(
            r"^ITEM\s+" + item, n.text.strip().upper())]
        logger.info("Sections: %d", len(sections))
        if len(sections) == 0:
            return ""
        item_node = sections[0]
        item_text = item_node.text + "\n\n" + \
            "\n".join([n.text for n in item_node.get_descendants()])
        logger.info("Item text: %d characters", len(item_text))
    except Exception as e:
        logger.info("Error getting 10-K item: %s", e)
    return item_text


# Initialize MCP server
# needed for toolw definitions below
mcp = FastMCP("stock-symbol-server", lifespan=app_lifespan)


@mcp.tool()
async def fetch_url_content(
    url: Annotated[
        str,
        {
            "description": "The URL to fetch content from",
            "example": "https://www.google.com"
        },
    ],
) -> str:
    """Get normalized text content from a URL. Use to fetch permissioned content where the password is saved in the Firefox profile."""
    try:
        mcp_context = mcp.get_context()
        app_context = mcp_context.request_context.lifespan_context
        extractor = app_context.stock_data_extractor
        wait_strategy = "networkidle"

        logger.info("URL: %s", url)

        extractor_response = await extractor.fetch_url(url, wait_strategy)
        if not extractor_response or extractor_response.get('status') != 'success':
            message = extractor_response.get(
                'message') if extractor_response else "Failed to get page content"
            return {
                "url": url,
                "status": "error",
                "message": message
            }

        content = extractor_response.get('content')

        if not content:
            return {
                "url": url,
                "status": "error",
                "message": "No content"
            }

        return {
            "url": url,
            "status": "success",
            "content": content,
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
async def fetch_url_html(
    url: Annotated[
        str,
        {
            "description": "The URL to fetch content from",
            "example": "https://www.google.com"
        },
    ],
) -> str:
    """Get raw html from a URL. Use to fetch permissioned content where the password is saved in the Firefox profile."""
    try:
        mcp_context = mcp.get_context()
        app_context = mcp_context.request_context.lifespan_context
        extractor = app_context.stock_data_extractor
        wait_strategy = "networkidle"

        logger.info("URL: %s", url)

        extractor_response = await extractor.fetch_url(url, wait_strategy, extract_mode="raw_html")
        if not extractor_response or extractor_response.get('status') != 'success':
            message = extractor_response.get(
                'message') if extractor_response else "Failed to get page content"
            return {
                "url": url,
                "status": "error",
                "message": message
            }

        content = extractor_response.get('content')

        if not content:
            return {
                "url": url,
                "status": "error",
                "message": "No content"
            }

        return {
            "url": url,
            "status": "success",
            "content": content,
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
async def fetch_url_links(
    url: Annotated[
        str,
        {
            "description": "The URL to fetch content from",
            "example": "https://www.google.com"
        },
    ],
) -> str:
    """Get the links from a web page. Use to fetch permissioned content where the password is saved in the Firefox profile."""
    try:
        mcp_context = mcp.get_context()
        app_context = mcp_context.request_context.lifespan_context
        extractor = app_context.stock_data_extractor
        wait_strategy = "networkidle"

        logger.info("URL: %s", url)

        extractor_response = await extractor.fetch_url(url, wait_strategy, extract_mode="links")
        if not extractor_response or extractor_response.get('status') != 'success':
            message = extractor_response.get(
                'message') if extractor_response else "Failed to get page content"
            return {
                "url": url,
                "status": "error",
                "message": message
            }

        content = extractor_response.get('content')

        if not content:
            return {
                "url": url,
                "status": "error",
                "message": "No content"
            }

        return {
            "url": url,
            "status": "success",
            "content": content,
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def fetch_10k_item1(symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ],
) -> str:
    """Get item 1 of the latest 10-K annual report filing for a given symbol."""
    return fn_get_10k_item_from_symbol(symbol)


@mcp.tool()
def fetch_peers(symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ],
) -> str:
    """Get industry comparables or peers for a stock symbol."""
    obb.account.login(email=os.environ['OPENBB_USER'],
                      password=os.environ['OPENBB_PW'], remember_me=True)

    obj = obb.equity.compare.peers(symbol=symbol, provider='fmp')
    peers = obj.results
    retstr = ""
    for peer in peers.peers_list:
        try:
            obj = obb.equity.profile(peer)
            results = obj.results[0]
            desc = ""
            if results.short_description:
                desc = results.short_description
            elif results.long_description:
                desc = results.long_description

            retstr += f"""
    Symbol:        {peer}
    Name:          {results.name}
    Country:       {results.hq_country}
    Industry:      {results.industry_category}
    Description:   {desc}
    """
        except Exception:
            continue
    return retstr


@mcp.tool()
async def fetch_technical_analysis(symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ],
) -> str:
    """Get technical analysis for a given symbol."""
    market_data = MarketData()
    tech_analysis = TechnicalAnalysis()
    tadf = await market_data.get_historical_data(symbol)
    tadf = tech_analysis.add_core_indicators(tadf)
    trend = tech_analysis.check_trend_status(tadf)
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

    Latest Price: ${tadf['close'].iloc[-1]:.2f}
    Average True Range (14): {tadf['atr'].iloc[-1]:.2f}
    Average Daily Range Percentage: {tadf['adrp'].iloc[-1]:.2f}%
    Average Volume (20D): {tadf['avg_20d_vol'].iloc[-1]}
    """
    return analysis

    # these don't show the image inline  in Claude desktop :(
    # you can send image bytes back but you have to expand tool response to see the image
    # @mcp.tool()
    # def return_relative_file_path():
    #     relative_path = os.path.relpath("charts/chart.png")
    #     return {
    #         "content": [
    #             {
    #                 "type": "image",
    #                 "source": {
    #                     "type": "url",
    #                     "url": f"file://{relative_path}"
    #                 }
    #             }
    #         ]
    #     }

    # @mcp.tool()
    # def return_absolute_file_path():
    #     absolute_path = os.path.abspath(
    #         "/Users/drucev/projects/windsurf/MCP/charts/chart.png")
    #     return {
    #         "content": [
    #             {
    #                 "type": "image",
    #                 "source": {
    #                     "type": "url",
    #                     "url": f"file://{absolute_path}"
    #                 }
    #             }
    #         ]
    #     }

    # @Server.list_resources()
    # async def list_resources():
    #     return [
    #         Resource(
    #             uri="file://charts/chart.png",
    #             name="Chart Image",
    #             mimeType="image/png"
    #         )
    #     ]

    # @Server.read_resource()
    # async def read_resource(uri: str):
    #     if uri == "file://charts/chart.png":
    #         with open("charts/chart.png", "rb") as f:
    #             return base64.b64encode(f.read()).decode()


@mcp.tool()
def make_stock_chart(symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ],
) -> MCPImage:
    """Return a stock chart for a given symbol."""

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
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        specs=[[{"secondary_y": True}], [{}]],  # row 1 has secondary y-axis
        subplot_titles=[
            f"{symbol} Price with Moving Averages & Volume", f"{symbol} Relative to S&P 500"]
    )

    # --- Row 1: Price Candlesticks & MAs (primary y-axis) ---
    fig.add_trace(go.Candlestick(
        x=symbol_df.index,
        open=symbol_df['Open'],
        high=symbol_df['High'],
        low=symbol_df['Low'],
        close=symbol_df['Close'],
        name=symbol,
        increasing_line_color='black',
        decreasing_line_color='red'
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['MA13'],
        mode='lines',
        name='13-week MA',
        line=dict(color='blue')
    ), row=1, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['MA52'],
        mode='lines',
        name='52-week MA',
        line=dict(color='orange')
    ), row=1, col=1, secondary_y=False)
    # --- Row 1: Volume on right axis (secondary y-axis) ---
    fig.add_trace(go.Bar(
        x=symbol_df.index,
        y=symbol_df['Volume'],
        name='Volume',
        marker_color='rgba(0, 128, 0, 0.4)',
        showlegend=False
    ), row=1, col=1, secondary_y=True)

    # --- Row 2: Relative to SPX ---
    fig.add_trace(go.Scatter(
        x=symbol_df.index,
        y=symbol_df['Rel_SPX'],
        name=symbol + ' / SPX',
        mode='lines',
        line=dict(color='black')
    ), row=2, col=1)

    # Layout adjustments
    fig.update_layout(
        title=symbol +
        ' Weekly Chart with MAs, Volume (Right Axis), and Relative Strength',
        height=800,
        xaxis=dict(rangeslider_visible=False),
        showlegend=True,
        # Add some margin for better display
        margin=dict(l=50, r=50, t=100, b=50)
    )

    fig.update_yaxes(title_text="Price", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text=f"{symbol} / SPX", row=2, col=1)

    # Convert the plot to a PNG image and return as FastMCP Image
    dt = datetime.now().strftime("%Y%m%d-%H%M%S.%f")[:-3]
    filename = f"charts/{symbol}_{dt}.png"
    fig.write_image(filename, width=800, height=600, scale=2)

    img_bytes = pio.to_image(fig, format="png", width=800, height=600)
    # Encode as base64
    # img_base64 = base64.b64encode(img_bytes).decode()

    # Return the relative file path
    return MCPImage(data=img_bytes, format="png")


@mcp.tool()
async def fetch_image_from_url(
    url: Annotated[
        str,
        {
            "description": "The URL of the image",
            "example": "https://example.com/image.jpg"
        }
    ],
) -> MCPImage:
    """Show an image based on a URL. The URL should point directly to an image."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Check if the response is actually an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                raise ValueError(
                    f"URL does not point to an image. Content-Type: {content_type}")

            image_data = response.content

            # Try to open with PIL to validate it's a valid image
            try:
                with PILImage.open(io.BytesIO(image_data)) as img:
                    # Convert to RGB if necessary and save as PNG
                    if img.mode in ('RGBA', 'LA', 'P'):
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                    elif img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGB')

                    # Save as PNG
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    processed_data = buffer.getvalue()

            except Exception as e:
                raise ValueError(f"Invalid image data: {e}") from e

            return MCPImage(data=processed_data, format="png")

    except httpx.TimeoutException as e:
        raise ValueError("Timeout while fetching image from URL") from e
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"HTTP error {e.response.status_code} while fetching image") from e
    except Exception as e:
        raise ValueError(f"Error fetching image: {str(e)}") from e

# TODO: news landing page tools should use a pattern and just return the urls of the news stories


@mcp.tool()
async def get_bloomberg_news(
    company: Annotated[
        str,
        {
            "description": "The name of the company",
            "example": "Tesla"
        }
    ],
) -> dict:
    """Search Bloomberg headlines for a given company name."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("bloomberg", company=company)


@mcp.tool()
async def get_reuters_news(
    company: Annotated[
        str,
        {
            "description": "The name of the company",
            "example": "Tesla"
        }
    ]
) -> dict:
    """Search Reuters headlines for a given company name."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("reuters", company=company)


@mcp.tool()
async def get_yahoo_news(
    symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ]
) -> dict:
    """Search Yahoo Finance headlines for a given stock symbol."""

    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("yahoo_news", symbol=symbol)


@mcp.tool()
async def get_yahoo_stats(
    symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "GOOG"
        }
    ]
) -> dict:
    """Search Yahoo Finance for key fundamental statistics for a given stock symbol."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("yahoo_stats", symbol=symbol)


# @mcp.tool()
# async def get_ft_news(
#     company: Annotated[
#         str,
#         {
#             "description": "The name of the company",
#             "example": "Goldman Sachs"
#         }
#     ]
# ) -> dict:
#     """Search Financial Times headlines for a given company name."""
#     return await fetch_source_content("ft", company=company)


# @mcp.tool()
# async def get_barrons_news_url(
#     symbol: Annotated[
#         str,
#         {
#             "description": "The stock symbol",
#             "example": "TSLA"
#         }
#     ],
#     company: Annotated[
#         str,
#         {
#             "description": "The name of the company",
#             "example": "Tesla Inc"
#         }
#     ]
# ) -> dict:
#     """Search Barron's headlines for a given stock symbol and company name."""
#     return await fetch_source_content("barrons", symbol=symbol, company=company)


@mcp.tool()
async def get_business_insider_news(
    company: Annotated[
        str,
        {
            "description": "The name of the company",
            "example": "Netflix"
        }
    ]
) -> dict:
    """Search Business Insider headlines for a given company name."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("business_insider", company=company)


@mcp.tool()
async def get_google_finance_news(
        symbol: Annotated[
            str,
            {
                "description": "The stock symbol",
                "example": "META"
            },
        ],
        exchange: Annotated[
            str,
            {
                "description": "The exchange where the stock is traded",
                "example": "NASDAQ"
            }
        ]) -> dict:
    """Search Google Finance for a given stock symbol."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("google_finance", symbol=symbol, exchange=exchange)

# # getting timeouts on morningstar, either needs debugging or they are blocking Playwright somehow


@mcp.tool()
async def get_morningstar_research(
    symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ],
    exchange: Annotated[
        str,
        {
            "description": "The exchange where the stock is traded",
            "example": "NASDAQ"
        }
    ]
) -> dict:
    """Search Morningstar for a given stock symbol and exchange."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("morningstar", symbol=symbol, exchange=exchange)


@mcp.tool()
async def get_finviz_news(
    symbol: Annotated[
        str,
        {
            "description": "The stock symbol",
            "example": "AAPL"
        }
    ]
) -> dict:
    """Search Finviz for a given stock symbol."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("finviz", symbol=symbol)


# @mcp.tool()
# async def get_whalewisdom_updates(
#     symbol: Annotated[
#         str,
#         {
#             "description": "The stock symbol",
#             "example": "AAPL"
#         }
#     ]
# ) -> dict:
#     """Search WhaleWisdom investor transaction updates for a given stock symbol."""
#     return await fetch_source_content("whalewisdom", symbol=symbol)


# @mcp.tool()
# async def get_gurufocus_news(
#     symbol: Annotated[
#         str,
#         {
#             "description": "The stock symbol",
#             "example": "AAPL"
#         }
#     ]
# ) -> dict:
#     """Search GuruFocus investor transaction updates for a given stock symbol."""
#     return await fetch_source_content("gurufocus", symbol=symbol)


@mcp.tool()
async def get_reddit_news(
    company: Annotated[
        str,
        {
            "description": "The name of the company",
            "example": "Tesla"
        }
    ]
) -> dict:
    """Search Reddit for a given company name."""
    context = mcp.get_context()
    app_context = context.request_context.lifespan_context
    extractor = app_context.stock_data_extractor
    return await extractor.fetch_source_content("reddit", company=company)

# @mcp.tool()
# def test_params(symbol: str, company: str, exchange: str) -> str:
#     """test tool, returns the parameters received.

#     Args:
#         symbol: The stock symbol (e.g., AAPL, MSFT)
#         company: The company name (e.g., Apple Inc.)
#         exchange: The exchange where the stock is traded (e.g., NASDAQ, NYSE)

#     Returns:
#         A formatted string with the received parameters
#     """
#     # Print parameters to console for debugging (as requested)
#     print("Received parameters:", file=sys.stderr)
#     print(f"  Symbol: {symbol}", file=sys.stderr)
#     print(f"  Company: {company}", file=sys.stderr)
#     print(f"  Exchange: {exchange}", file=sys.stderr)

#     # Return the symbols received (as requested)
#     result = "Stock Symbol Information:\n"
#     result += f"Symbol: {symbol}\n"
#     result += f"Company: {company}\n"
#     result += f"Exchange: {exchange}"

#     return result

# TODO: add get_urls to sources.yaml
# bring over url extraction code from AInewsbot scrape, either in exraction object or scrape module
# when get_urls is present, extract urls and return urls as markdown instead of whole page


def main():
    """Main entry point for the MCP server."""
    # Load and display available sources
    with open(SOURCES, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    loaded_sources = {}
    for key, source_data in config['sources'].items():
        loaded_sources[key] = SourceConfig(**source_data)
    logger.info("Successfully loaded %d sources", len(loaded_sources))

    loaded_exchanges = config.get('exchange_mappings', {})
    for exchange_name in loaded_exchanges:
        logger.info("Loaded exchange mapping for %s", exchange_name)

    logger.info("MCP Server - Stock Research")
    logger.info("==========================")
    logger.info("\nAvailable sources:")
    for source_id, source in loaded_sources.items():
        logger.info("- %s (ID: %s)", source.name, source_id)
        logger.info("  Data type: %s", source.data_type)
        logger.info("  Required params: %s", ", ".join(source.required_params))

    logger.info("\nAvailable exchange mappings:")
    for exchange_name, mapping in loaded_exchanges.items():
        logger.info("- %s: %d mappings", exchange_name, len(mapping))

    # Run the server using stdio transport
    # Start the server using stdio transport and a browser context
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
