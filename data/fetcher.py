"""yfinance data fetcher with caching and validation."""

import time
from typing import Optional

import pandas as pd
import yfinance as yf

from config.settings import CACHE_TTL_SECONDS, DEFAULT_INTERVAL, DEFAULT_PERIOD

_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def fetch_ohlcv(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """Fetch OHLCV data for a ticker with caching.

    Returns a DataFrame with columns: Open, High, Low, Close, Volume.
    Index is DatetimeIndex.

    Raises ValueError if ticker is invalid or no data returned.
    """
    cache_key = f"{ticker}|{period}|{interval}"
    now = time.time()

    if cache_key in _cache:
        cached_time, cached_df = _cache[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_df.copy()

    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
    except Exception as e:
        raise ValueError(f"Failed to fetch data for '{ticker}': {e}")

    if df is None or df.empty:
        raise ValueError(
            f"No data returned for '{ticker}'. Check that the ticker symbol is valid."
        )

    # Keep only OHLCV columns
    expected_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    df = df[expected_cols].copy()
    df.dropna(inplace=True)

    if len(df) < 2:
        raise ValueError(f"Insufficient data for '{ticker}' (got {len(df)} rows).")

    _cache[cache_key] = (now, df.copy())
    return df


def get_asset_info(ticker: str) -> Optional[dict]:
    """Fetch basic asset info (name, sector, market cap, etc.)."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "N/A"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception:
        return None
