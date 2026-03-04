"""Macro regime indicators: Copper-Gold Ratio, VIX Term Structure.

These indicators fetch cross-asset data to gauge macroeconomic conditions
and market-wide risk appetite.  Signals apply broadly to all equities.

- Copper-Gold Ratio: industrial vs. safe-haven demand → economic cycle proxy
- VIX Term Structure: near-term vs. 3-month implied vol → fear / complacency
"""

from typing import Any

import numpy as np
import pandas as pd

from indicators._utils import align_to_index, fetch_reference_close
from indicators.base import BaseIndicator
from indicators.registry import register
from signals.base import SignalDirection, SignalResult


# ---------------------------------------------------------------------------
# Copper-Gold Ratio
# ---------------------------------------------------------------------------

@register
class CopperGoldRatio(BaseIndicator):
    """Copper / Gold price ratio as an economic cycle indicator.

    A rising ratio signals industrial expansion (bullish for equities);
    a falling ratio signals contraction / flight-to-safety (bearish).
    Research shows the ratio is a leading indicator for 3-12 month equity
    returns and Treasury yields.
    """

    SMA_SHORT = 50
    SMA_LONG = 200

    @property
    def name(self) -> str:
        return "Copper-Gold Ratio"

    @property
    def category(self) -> str:
        return "macro"

    @property
    def lookback(self) -> int:
        return self.SMA_LONG

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        copper = fetch_reference_close("HG=F")
        gold = fetch_reference_close("GC=F")

        copper_aligned = align_to_index(copper, df.index)
        gold_aligned = align_to_index(gold, df.index)

        ratio = copper_aligned / gold_aligned
        ratio = ratio.replace([np.inf, -np.inf], np.nan)

        df["CG_ratio"] = ratio
        df["CG_SMA_short"] = ratio.rolling(window=self.SMA_SHORT, min_periods=1).mean()
        df["CG_SMA_long"] = ratio.rolling(window=self.SMA_LONG, min_periods=1).mean()
        df["CG_roc"] = ratio.pct_change(periods=20, fill_method=None)

        return df

    def get_signal(self, df: pd.DataFrame, idx: int = -1) -> SignalResult:
        if "CG_ratio" not in df.columns:
            df = self.compute(df)

        ratio = df["CG_ratio"].iloc[idx]
        sma_s = df["CG_SMA_short"].iloc[idx]
        sma_l = df["CG_SMA_long"].iloc[idx]
        roc = df["CG_roc"].iloc[idx]

        if pd.isna(ratio) or pd.isna(sma_s) or pd.isna(sma_l):
            return SignalResult(self.name, SignalDirection.HOLD, 0.0,
                                "Reference data unavailable")

        roc_conf = abs(roc) * 5 if not pd.isna(roc) else 0.3

        # Ratio above both SMAs → expansion → bullish
        if ratio > sma_s and sma_s > sma_l:
            confidence = min(0.8, roc_conf)
            return SignalResult(self.name, SignalDirection.BUY, confidence,
                                f"Cu/Au ratio in uptrend ({ratio:.5f}), economic expansion")

        # Ratio below both SMAs → contraction → bearish
        if ratio < sma_s and sma_s < sma_l:
            confidence = min(0.8, roc_conf)
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"Cu/Au ratio in downtrend ({ratio:.5f}), economic contraction")

        # Transitional: ratio vs short-term SMA only
        if ratio > sma_s:
            confidence = min(0.4, roc_conf * 0.6)
            return SignalResult(self.name, SignalDirection.BUY, confidence,
                                f"Cu/Au ratio above short-term avg ({ratio:.5f})")

        if ratio < sma_s:
            confidence = min(0.4, roc_conf * 0.6)
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"Cu/Au ratio below short-term avg ({ratio:.5f})")

        return SignalResult(self.name, SignalDirection.HOLD, 0.0,
                            f"Cu/Au ratio neutral ({ratio:.5f})")

    def get_chart_config(self) -> dict[str, Any]:
        return {
            "overlay": False,
            "columns": ["CG_ratio", "CG_SMA_short", "CG_SMA_long"],
            "colors": {
                "CG_ratio": "#FF5722",
                "CG_SMA_short": "#2196F3",
                "CG_SMA_long": "#FF9800",
            },
            "subplot_title": "Copper-Gold Ratio",
        }


# ---------------------------------------------------------------------------
# VIX Term Structure
# ---------------------------------------------------------------------------

@register
class VIXTermStructure(BaseIndicator):
    """VIX term structure (near-term vs. 3-month) as a fear / complacency gauge.

    Backwardation (VIX > VIX3M) signals acute market stress and historically
    precedes further equity downside.  Normal contango (VIX < VIX3M) signals
    relative calm.  Extreme complacency (very low VIX + deep contango) can
    also precede sharp reversals.
    """

    @property
    def name(self) -> str:
        return "VIX Term Structure"

    @property
    def category(self) -> str:
        return "macro"

    @property
    def lookback(self) -> int:
        return 20

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        vix = fetch_reference_close("^VIX")
        vix3m = fetch_reference_close("^VIX3M")

        vix_aligned = align_to_index(vix, df.index)
        vix3m_aligned = align_to_index(vix3m, df.index)

        df["VIX"] = vix_aligned
        df["VIX3M"] = vix3m_aligned
        # Positive spread = contango (normal), negative = backwardation (stress)
        df["VIX_spread"] = vix3m_aligned - vix_aligned
        df["VIX_ratio"] = vix_aligned / vix3m_aligned

        return df

    def get_signal(self, df: pd.DataFrame, idx: int = -1) -> SignalResult:
        if "VIX" not in df.columns:
            df = self.compute(df)

        vix = df["VIX"].iloc[idx]
        vix3m = df["VIX3M"].iloc[idx]
        ratio = df["VIX_ratio"].iloc[idx]

        if pd.isna(vix) or pd.isna(vix3m) or vix3m == 0:
            return SignalResult(self.name, SignalDirection.HOLD, 0.0,
                                "VIX data unavailable")

        # Severe backwardation: VIX >> VIX3M → acute stress
        if ratio > 1.10:
            confidence = min(0.9, (ratio - 1.0) * 2)
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"VIX backwardation ({vix:.1f} vs {vix3m:.1f}), acute market stress")

        # Mild backwardation
        if ratio > 1.0:
            confidence = min(0.6, (ratio - 1.0) * 5)
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"VIX mildly inverted ({vix:.1f} vs {vix3m:.1f}), elevated stress")

        # Extreme complacency — deep contango with very low VIX
        if vix < 13 and ratio < 0.85:
            return SignalResult(self.name, SignalDirection.HOLD, 0.3,
                                f"Extreme complacency (VIX={vix:.1f}), watch for reversal")

        # Normal contango → mildly bullish
        if ratio < 0.95:
            confidence = min(0.5, (1.0 - ratio) * 3)
            return SignalResult(self.name, SignalDirection.BUY, confidence,
                                f"Normal VIX contango ({vix:.1f} vs {vix3m:.1f}), calm markets")

        # Near parity
        return SignalResult(self.name, SignalDirection.HOLD, 0.1,
                            f"VIX near parity ({vix:.1f} vs {vix3m:.1f})")

    def get_chart_config(self) -> dict[str, Any]:
        return {
            "overlay": False,
            "columns": ["VIX", "VIX3M"],
            "colors": {"VIX": "#F44336", "VIX3M": "#4CAF50"},
            "subplot_title": "VIX Term Structure",
        }
