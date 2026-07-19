"""Tests for data fetcher utility functions.

Note: fetch_ohlcv and other @st.cache_data functions are not tested here
because they depend on Streamlit runtime. We test pure utility functions only.
"""

import pandas as pd
import pytest

from data.fetcher import (
    compute_buy_and_hold,
    compute_open_to_close_return,
    is_crypto_ticker,
    slice_date_range,
    trim_to_period,
)


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


class TestOpenToCloseReturn:
    def test_uses_first_open_and_last_close(self):
        df = pd.DataFrame({"Open": [90.0, 105.0], "Close": [100.0, 110.0]})
        assert compute_open_to_close_return(df) == pytest.approx(110.0 / 90.0 - 1.0)


class TestPeriodSlicing:
    def test_trim_to_requested_period(self):
        index = pd.date_range("2023-01-01", periods=800, freq="D")
        df = pd.DataFrame({"Close": range(800)}, index=index)
        result = trim_to_period(df, "1y")
        assert result.index[0] >= df.index[-1] - pd.Timedelta(days=365)
        assert len(result) < len(df)

    def test_slice_date_range_ignores_timezone_difference(self):
        index = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        df = pd.DataFrame({"Close": range(10)}, index=index)
        result = slice_date_range(
            df,
            pd.Timestamp("2024-01-03", tz="America/New_York"),
            pd.Timestamp("2024-01-05", tz="America/New_York"),
        )
        assert list(result.index.day) == [3, 4, 5]
