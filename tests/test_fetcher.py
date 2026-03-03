"""Tests for data fetcher utility functions.

Note: fetch_ohlcv and other @st.cache_data functions are not tested here
because they depend on Streamlit runtime. We test pure utility functions only.
"""

import pandas as pd
import pytest

from data.fetcher import compute_buy_and_hold, is_crypto_ticker


class TestIsCryptoTicker:
    def test_crypto_usd(self):
        assert is_crypto_ticker("BTC-USD") is True
        assert is_crypto_ticker("ETH-USD") is True

    def test_crypto_other_currencies(self):
        assert is_crypto_ticker("BTC-EUR") is True
        assert is_crypto_ticker("ETH-GBP") is True
        assert is_crypto_ticker("SOL-USDT") is True
        assert is_crypto_ticker("AVAX-BUSD") is True

    def test_stock_tickers(self):
        assert is_crypto_ticker("AAPL") is False
        assert is_crypto_ticker("MSFT") is False
        assert is_crypto_ticker("GOOGL") is False

    def test_case_insensitive(self):
        assert is_crypto_ticker("btc-usd") is True
        assert is_crypto_ticker("Eth-Eur") is True

    def test_indices(self):
        assert is_crypto_ticker("^GSPC") is False
        assert is_crypto_ticker("^DJI") is False


class TestComputeBuyAndHold:
    def test_normal_positive(self):
        df = pd.DataFrame({"Close": [100.0, 110.0, 120.0]})
        result = compute_buy_and_hold(df)
        assert result == pytest.approx(0.2)

    def test_normal_negative(self):
        df = pd.DataFrame({"Close": [100.0, 90.0, 80.0]})
        result = compute_buy_and_hold(df)
        assert result == pytest.approx(-0.2)

    def test_insufficient_data(self):
        df = pd.DataFrame({"Close": [100.0]})
        assert compute_buy_and_hold(df) is None

    def test_none_input(self):
        assert compute_buy_and_hold(None) is None

    def test_zero_price(self):
        df = pd.DataFrame({"Close": [0.0, 100.0]})
        assert compute_buy_and_hold(df) is None

    def test_empty_dataframe(self):
        df = pd.DataFrame({"Close": []})
        assert compute_buy_and_hold(df) is None
