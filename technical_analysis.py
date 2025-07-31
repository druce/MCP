
# https://sethhobson.com/2025/01/building-a-stock-analysis-server-with-mcp-part-1/

import pandas as pd
import aiohttp
from datetime import datetime, timedelta
import os
from typing import Any, Dict
import numpy as np
np.NaN = np.nan
# must be last import after patching NaN
import pandas_ta as ta


# pylint: disable=broad-except


class MarketDataError(Exception):
    """Raised for unexpected errors while fetching market data."""


class MarketData:
    """Handles all market data fetching operations."""

    def __init__(self):
        self.api_key = os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("TIINGO_API_KEY not found in environment")

        self.headers = {"Content-Type": "application/json",
                        "Authorization": f"Token {self.api_key}"}

    async def get_historical_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
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
                f"Network error while fetching data for {symbol}: {e}") from e
        except ValueError as ve:
            raise ve  # Propagate value errors (symbol issues, no data, etc.)
        except Exception as e:  # pylint: disable=broad-except
            raise MarketDataError(
                f"Unexpected error fetching data for {symbol}: {e}") from e


class TechnicalAnalysis:
    """Technical analysis toolkit with improved performance and readability."""

    @staticmethod
    def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add a core set of technical indicators."""
        try:
            # Adding trend indicators
            df["sma_20"] = ta.sma(df["close"], length=20)
            df["sma_50"] = ta.sma(df["close"], length=50)
            df["sma_200"] = ta.sma(df["close"], length=200)

            # Adding volatility indicators and volume
            daily_range = df["high"].sub(df["low"])
            adr = daily_range.rolling(window=20).mean()
            df["adrp"] = adr.div(df["close"]).mul(100)
            df["avg_20d_vol"] = df["volume"].rolling(window=20).mean()

            # Adding momentum indicators
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
            df["rsi"] = ta.rsi(df["close"], length=14)
            macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if macd is not None:
                df = pd.concat([df, macd], axis=1)

            return df

        except KeyError as e:
            raise KeyError(
                f'Missing column in input DataFrame: {str(e)}') from e
        except Exception as e:
            raise MarketDataError(
                f"Unexpected error computing pandas data: {e}") from e

    @staticmethod
    def check_trend_status(df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze the current trend status."""
        if df.empty:
            raise ValueError(
                "DataFrame is empty. Ensure it contains valid data.")

        latest = df.iloc[-1]
        return {
            "above_20sma": latest["close"] > latest["sma_20"],
            "above_50sma": latest["close"] > latest["sma_50"],
            "above_200sma": latest["close"] > latest["sma_200"],
            "20_50_bullish": latest["sma_20"] > latest["sma_50"],
            "50_200_bullish": latest["sma_50"] > latest["sma_200"],
            "rsi": latest["rsi"],
            "macd_bullish": latest.get("MACD_12_26_9", 0) > latest.get("MACDs_12_26_9", 0),
        }
