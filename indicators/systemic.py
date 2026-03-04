"""Systemic risk indicators: Market Correlation Regime (Absorption Ratio).

Tracks interconnectedness of S&P 500 sector ETFs using eigenvalue analysis
of the rolling correlation matrix.  When the first eigenvalue dominates
(high absorption ratio), cross-sector correlations are elevated and
diversification fails — a precursor to systemic selloffs.

Reference: Kritzman, Li, Page & Rigobon (2011), "Principal Components as
a Measure of Systemic Risk".
"""

from typing import Any

import numpy as np
import pandas as pd

from indicators._utils import align_to_index, fetch_reference_close
from indicators.base import BaseIndicator
from indicators.registry import register
from signals.base import SignalDirection, SignalResult

# S&P 500 sector ETFs
SECTOR_ETFS = [
    "XLF", "XLK", "XLE", "XLV", "XLI",
    "XLU", "XLY", "XLP", "XLB", "XLRE", "XLC",
]


def _fetch_sector_returns(target_index: pd.DatetimeIndex) -> "pd.DataFrame | None":
    """Fetch daily returns for sector ETFs aligned to the target index."""
    sector_closes: dict[str, pd.Series] = {}

    for etf in SECTOR_ETFS:
        closes = fetch_reference_close(etf, period="2y")
        if closes is not None:
            aligned = align_to_index(closes, target_index)
            sector_closes[etf] = aligned

    if len(sector_closes) < 5:
        return None

    closes_df = pd.DataFrame(sector_closes)
    returns_df = closes_df.pct_change(fill_method=None)
    return returns_df


@register
class MarketCorrelation(BaseIndicator):
    """Market correlation regime via absorption ratio.

    The absorption ratio is the fraction of total variance captured by the
    first eigenvalue of the sector-ETF correlation matrix.  When AR > 0.5,
    markets are tightly coupled, diversification is breaking down, and the
    probability of a correlated selloff is elevated.
    """

    CORR_WINDOW = 60

    @property
    def name(self) -> str:
        return "Market Correlation"

    @property
    def category(self) -> str:
        return "systemic"

    @property
    def lookback(self) -> int:
        return self.CORR_WINDOW

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        n = len(df)

        sector_returns = _fetch_sector_returns(df.index)

        absorption = np.full(n, np.nan)
        top_eigenvalue = np.full(n, np.nan)

        if sector_returns is not None and len(sector_returns) >= self.CORR_WINDOW:
            for i in range(self.CORR_WINDOW, min(n, len(sector_returns))):
                window = sector_returns.iloc[i - self.CORR_WINDOW : i]
                window = window.dropna(axis=1, how="any")

                if window.shape[1] < 3 or window.shape[0] < self.CORR_WINDOW // 2:
                    continue

                try:
                    corr = window.corr().values
                    if np.isnan(corr).any():
                        continue
                    eigenvalues = np.sort(np.linalg.eigvalsh(corr))[::-1]
                    total = eigenvalues.sum()
                    if total > 0:
                        absorption[i] = eigenvalues[0] / total
                        top_eigenvalue[i] = eigenvalues[0]
                except (np.linalg.LinAlgError, ValueError):
                    continue

        df["AbsorptionRatio"] = absorption
        df["TopEigenvalue"] = top_eigenvalue

        return df

    def get_signal(self, df: pd.DataFrame, idx: int = -1) -> SignalResult:
        if "AbsorptionRatio" not in df.columns:
            df = self.compute(df)

        ar = df["AbsorptionRatio"].iloc[idx]

        if pd.isna(ar):
            return SignalResult(self.name, SignalDirection.HOLD, 0.0,
                                "Sector data unavailable")

        # Z-score vs. recent history
        actual_idx = idx if idx >= 0 else len(df) + idx
        start = max(0, actual_idx - 60)
        history = df["AbsorptionRatio"].iloc[start : actual_idx + 1].dropna()

        if len(history) > 5:
            ar_mean = history.mean()
            ar_std = history.std()
            z_score = (ar - ar_mean) / ar_std if ar_std > 0 else 0.0
        else:
            z_score = 0.0

        # Very high absorption → systemic fragility → SELL
        if ar > 0.55 or z_score > 1.5:
            confidence = min(0.8, max(0.4, ar, z_score * 0.2))
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"High market correlation (AR={ar:.3f}), systemic risk elevated")

        # Moderately high
        if ar > 0.45 or z_score > 0.75:
            confidence = min(0.5, ar)
            return SignalResult(self.name, SignalDirection.SELL, confidence,
                                f"Above-average correlation (AR={ar:.3f}), caution")

        # Low absorption → healthy diversification → mild BUY
        if ar < 0.30 or z_score < -1.0:
            confidence = min(0.5, max(0.2, (0.4 - ar) * 3))
            return SignalResult(self.name, SignalDirection.BUY, confidence,
                                f"Low market correlation (AR={ar:.3f}), healthy diversification")

        return SignalResult(self.name, SignalDirection.HOLD, 0.1,
                            f"Normal market correlation (AR={ar:.3f})")

    def get_chart_config(self) -> dict[str, Any]:
        return {
            "overlay": False,
            "columns": ["AbsorptionRatio"],
            "colors": {"AbsorptionRatio": "#E91E63"},
            "subplot_title": "Absorption Ratio (Systemic Risk)",
        }
