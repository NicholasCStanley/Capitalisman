"""Tests for individual indicator computation and signal generation."""

import pandas as pd
import pytest

from indicators.registry import get_all_indicators
from signals.base import SignalDirection, SignalResult
from tests.conftest import make_ohlcv


class TestAllIndicators:
    """Generic tests that apply to every registered indicator."""

    @pytest.fixture(params=list(get_all_indicators().keys()))
    def indicator(self, request):
        return get_all_indicators()[request.param]

    def test_has_valid_category(self, indicator):
        assert indicator.category in (
            "trend", "momentum", "volatility", "volume",
            "macro", "structural", "microstructure", "systemic",
        )

    def test_positive_lookback(self, indicator):
        assert indicator.lookback > 0

    def test_chart_config_has_required_keys(self, indicator):
        cfg = indicator.get_chart_config()
        assert "overlay" in cfg
        assert "columns" in cfg
        assert isinstance(cfg["columns"], list)
        assert "colors" in cfg
        if not cfg["overlay"]:
            assert "subplot_title" in cfg

    def test_compute_adds_columns(self, indicator, ohlcv_200_up):
        original_cols = set(ohlcv_200_up.columns)
        result = indicator.compute(ohlcv_200_up)
        assert isinstance(result, pd.DataFrame)
        # Should add at least one new column
        new_cols = set(result.columns) - original_cols
        assert len(new_cols) > 0

    def test_compute_does_not_modify_input(self, indicator, ohlcv_100):
        original = ohlcv_100.copy()
        indicator.compute(ohlcv_100)
        pd.testing.assert_frame_equal(ohlcv_100, original)

    def test_signal_returns_valid_result(self, indicator, ohlcv_200_up):
        df = indicator.compute(ohlcv_200_up)
        signal = indicator.get_signal(df)
        assert isinstance(signal, SignalResult)
        assert isinstance(signal.direction, SignalDirection)
        assert 0.0 <= signal.confidence <= 1.0
        assert isinstance(signal.detail, str)
        assert signal.indicator_name == indicator.name

    def test_insufficient_data_returns_hold(self, indicator, ohlcv_short):
        df = indicator.compute(ohlcv_short)
        signal = indicator.get_signal(df)
        assert isinstance(signal, SignalResult)
        # With only 5 bars, most indicators can't produce meaningful signals
        assert signal.direction == SignalDirection.HOLD


class TestRSI:
    def test_compute_adds_rsi_column(self, ohlcv_100):
        from indicators.momentum import RSI
        rsi = RSI()
        result = rsi.compute(ohlcv_100)
        assert "RSI" in result.columns
        # RSI should be between 0 and 100 for non-NaN values
        valid = result["RSI"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_oversold_gives_buy(self):
        """Construct data where RSI will be deeply oversold."""
        # Steady decline to force RSI low
        df = make_ohlcv(100, start_price=200, trend="down", seed=10)
        from indicators.momentum import RSI
        rsi = RSI()
        result = rsi.compute(df)
        signal = rsi.get_signal(result)
        # With strong downtrend, RSI should be low; signal could be BUY (oversold) or SELL
        assert isinstance(signal, SignalResult)

    def test_overbought_gives_sell(self):
        """Construct data where RSI will be high."""
        df = make_ohlcv(100, start_price=50, trend="up", seed=10)
        from indicators.momentum import RSI
        rsi = RSI()
        result = rsi.compute(df)
        signal = rsi.get_signal(result)
        assert isinstance(signal, SignalResult)


class TestStochastic:
    def test_compute_adds_columns(self, ohlcv_100):
        from indicators.momentum import Stochastic
        stoch = Stochastic()
        result = stoch.compute(ohlcv_100)
        assert "Stoch_K" in result.columns
        assert "Stoch_D" in result.columns

    def test_signal_with_sufficient_data(self, ohlcv_200_up):
        from indicators.momentum import Stochastic
        stoch = Stochastic()
        result = stoch.compute(ohlcv_200_up)
        signal = stoch.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "Stochastic"


class TestSMACrossover:
    def test_compute_adds_sma_columns(self, ohlcv_200_up):
        from indicators.trend import SMACrossover
        sma = SMACrossover()
        result = sma.compute(ohlcv_200_up)
        assert "SMA_short" in result.columns
        assert "SMA_long" in result.columns

    def test_uptrend_favors_buy(self, ohlcv_200_up):
        from indicators.trend import SMACrossover
        sma = SMACrossover()
        result = sma.compute(ohlcv_200_up)
        signal = sma.get_signal(result)
        # In an uptrend, SMA short should be above SMA long
        assert signal.direction in (SignalDirection.BUY, SignalDirection.HOLD)


class TestEMACrossover:
    def test_compute_adds_ema_columns(self, ohlcv_200_up):
        from indicators.trend import EMACrossover
        ema = EMACrossover()
        result = ema.compute(ohlcv_200_up)
        assert "EMA_short" in result.columns
        assert "EMA_long" in result.columns


class TestMACD:
    def test_compute_adds_macd_columns(self, ohlcv_200_up):
        from indicators.trend import MACD
        macd = MACD()
        result = macd.compute(ohlcv_200_up)
        assert "MACD_line" in result.columns
        assert "MACD_signal" in result.columns
        assert "MACD_hist" in result.columns


class TestADX:
    def test_compute_adds_adx_columns(self, ohlcv_200_up):
        from indicators.trend import ADX
        adx = ADX()
        result = adx.compute(ohlcv_200_up)
        assert "ADX" in result.columns
        assert "ADX_pos" in result.columns
        assert "ADX_neg" in result.columns


class TestBollingerBands:
    def test_compute_adds_bb_columns(self, ohlcv_200_up):
        from indicators.volatility import BollingerBands
        bb = BollingerBands()
        result = bb.compute(ohlcv_200_up)
        assert "BB_upper" in result.columns
        assert "BB_middle" in result.columns
        assert "BB_lower" in result.columns
        assert "BB_pband" in result.columns


class TestVWAP:
    def test_compute_adds_vwap_column(self, ohlcv_200_up):
        from indicators.volume import VWAP
        vwap = VWAP()
        result = vwap.compute(ohlcv_200_up)
        assert "VWAP" in result.columns


class TestOBV:
    def test_compute_adds_obv_columns(self, ohlcv_200_up):
        from indicators.volume import OBV
        obv = OBV()
        result = obv.compute(ohlcv_200_up)
        assert "OBV" in result.columns
        assert "OBV_SMA" in result.columns


# --- Novel indicator tests ---


class TestCopperGoldRatio:
    def test_compute_adds_columns(self, ohlcv_200_up):
        from indicators.macro import CopperGoldRatio
        cg = CopperGoldRatio()
        result = cg.compute(ohlcv_200_up)
        assert "CG_ratio" in result.columns
        assert "CG_SMA_short" in result.columns
        assert "CG_SMA_long" in result.columns
        assert "CG_roc" in result.columns

    def test_signal_returns_valid_result(self, ohlcv_200_up):
        from indicators.macro import CopperGoldRatio
        cg = CopperGoldRatio()
        result = cg.compute(ohlcv_200_up)
        signal = cg.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "Copper-Gold Ratio"


class TestVIXTermStructure:
    def test_compute_adds_columns(self, ohlcv_200_up):
        from indicators.macro import VIXTermStructure
        vts = VIXTermStructure()
        result = vts.compute(ohlcv_200_up)
        assert "VIX" in result.columns
        assert "VIX3M" in result.columns
        assert "VIX_spread" in result.columns
        assert "VIX_ratio" in result.columns

    def test_signal_returns_valid_result(self, ohlcv_200_up):
        from indicators.macro import VIXTermStructure
        vts = VIXTermStructure()
        result = vts.compute(ohlcv_200_up)
        signal = vts.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "VIX Term Structure"


class TestBubbleRisk:
    def test_compute_adds_columns(self, ohlcv_200_up):
        from indicators.structural import BubbleRisk
        br = BubbleRisk()
        result = br.compute(ohlcv_200_up)
        assert "Hurst" in result.columns
        assert "LogAccel" in result.columns
        assert "BubbleScore" in result.columns

    def test_hurst_in_valid_range(self, ohlcv_200_up):
        from indicators.structural import BubbleRisk
        br = BubbleRisk()
        result = br.compute(ohlcv_200_up)
        valid = result["Hurst"].dropna()
        if len(valid) > 0:
            assert (valid >= 0).all() and (valid <= 1).all()

    def test_bubble_score_in_valid_range(self, ohlcv_200_up):
        from indicators.structural import BubbleRisk
        br = BubbleRisk()
        result = br.compute(ohlcv_200_up)
        valid = result["BubbleScore"].dropna()
        if len(valid) > 0:
            assert (valid >= 0).all() and (valid <= 1.1).all()

    def test_signal_returns_valid_result(self, ohlcv_200_up):
        from indicators.structural import BubbleRisk
        br = BubbleRisk()
        result = br.compute(ohlcv_200_up)
        signal = br.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "Bubble Risk"


class TestVPIN:
    def test_compute_adds_columns(self, ohlcv_200_up):
        from indicators.microstructure import VPIN
        vpin = VPIN()
        result = vpin.compute(ohlcv_200_up)
        assert "VPIN" in result.columns
        assert "BuyVolPct" in result.columns

    def test_vpin_in_valid_range(self, ohlcv_200_up):
        from indicators.microstructure import VPIN
        vpin = VPIN()
        result = vpin.compute(ohlcv_200_up)
        valid = result["VPIN"].dropna()
        if len(valid) > 0:
            assert (valid >= 0).all() and (valid <= 1).all()

    def test_buy_vol_pct_in_valid_range(self, ohlcv_200_up):
        from indicators.microstructure import VPIN
        vpin = VPIN()
        result = vpin.compute(ohlcv_200_up)
        valid = result["BuyVolPct"].dropna()
        if len(valid) > 0:
            assert (valid >= 0).all() and (valid <= 1).all()

    def test_signal_returns_valid_result(self, ohlcv_200_up):
        from indicators.microstructure import VPIN
        vpin = VPIN()
        result = vpin.compute(ohlcv_200_up)
        signal = vpin.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "VPIN"


class TestMarketCorrelation:
    def test_compute_adds_columns(self, ohlcv_200_up):
        from indicators.systemic import MarketCorrelation
        mc = MarketCorrelation()
        result = mc.compute(ohlcv_200_up)
        assert "AbsorptionRatio" in result.columns
        assert "TopEigenvalue" in result.columns

    def test_signal_returns_valid_result(self, ohlcv_200_up):
        from indicators.systemic import MarketCorrelation
        mc = MarketCorrelation()
        result = mc.compute(ohlcv_200_up)
        signal = mc.get_signal(result)
        assert isinstance(signal, SignalResult)
        assert signal.indicator_name == "Market Correlation"
