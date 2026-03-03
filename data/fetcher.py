"""yfinance data fetcher with caching and validation."""

from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf

from config.settings import CACHE_TTL_SECONDS, DEFAULT_INTERVAL, DEFAULT_PERIOD


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_raw(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Fetch and validate OHLCV data (cached by Streamlit)."""
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

    return df


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
    return _fetch_raw(ticker, period, interval).copy()


def is_crypto_ticker(ticker: str) -> bool:
    """Heuristic check for crypto tickers (e.g. BTC-USD, ETH-EUR)."""
    crypto_suffixes = ("-USD", "-USDT", "-EUR", "-GBP", "-BTC", "-ETH", "-BUSD")
    upper = ticker.upper()
    return any(upper.endswith(s) for s in crypto_suffixes)


def compute_buy_and_hold(df: pd.DataFrame) -> float | None:
    """Compute buy-and-hold return from the first to last close in a DataFrame.

    Returns the fractional return (e.g. 0.15 for +15%), or None if insufficient data.
    """
    if df is None or len(df) < 2:
        return None
    first_close = df["Close"].iloc[0]
    last_close = df["Close"].iloc[-1]
    if first_close == 0:
        return None
    return (last_close - first_close) / first_close


@st.cache_data(ttl=60, show_spinner=False)
def search_tickers(query: str) -> list[dict]:
    """Search for tickers using Yahoo Finance search API.

    Returns list of dicts with keys: symbol, name, exchange, type.
    """
    if not query or not query.strip():
        return []
    try:
        results = yf.Search(query)
        quotes = results.quotes if hasattr(results, "quotes") else []
        return [
            {
                "symbol": q.get("symbol", ""),
                "name": q.get("shortname") or q.get("longname", ""),
                "exchange": q.get("exchange", ""),
                "type": q.get("quoteType", ""),
            }
            for q in quotes
            if q.get("symbol")
        ]
    except Exception:
        return []


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
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
