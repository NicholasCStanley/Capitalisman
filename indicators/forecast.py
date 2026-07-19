"""TimesFM price forecast indicator.

Uses Google's TimesFM foundation model for zero-shot time series forecasting.
Provides an ML-based directional signal that is orthogonal to the rules-based
technical indicators in the rest of the system.

TimesFM is trained on billions of real-world time series and can capture
nonlinear patterns, regime changes, and seasonality that traditional
indicators miss.

Requires:  pip install timesfm torch
Optional — falls back to HOLD with zero confidence if not installed.
On first run the model (~800 MB) is downloaded from HuggingFace.
"""

from typing import Any

import numpy as np
import pandas as pd

from indicators.base import BaseIndicator
from indicators.registry import register
from signals.base import SignalDirection, SignalResult

# ---------------------------------------------------------------------------
# Model singleton — loaded once per process, reused across all calls.
# ---------------------------------------------------------------------------

_model = None
_model_load_attempted = False

FORECAST_HORIZON = 10  # days ahead
CONTEXT_LEN = 512      # max bars of history fed to the model
FORECAST_STEP = 10     # compute a new forecast every N bars (for backtesting)


def _get_model():
    """Lazy-load the TimesFM model with caching."""
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True

    try:
        import timesfm  # noqa: F811

        # TimesFM 2.0 API (dataclass-based config)
        try:
            _model = timesfm.TimesFm(
                hparams=timesfm.TimesFmHparams(
                    backend="cpu",
                    per_core_batch_size=32,
                    horizon_len=FORECAST_HORIZON,
                    context_len=CONTEXT_LEN,
                ),
                checkpoint=timesfm.TimesFmCheckpoint(
                    huggingface_repo_id="google/timesfm-2.0-200m-pytorch",
                ),
            )
            return _model
        except (AttributeError, TypeError):
            pass

        # TimesFM 1.0 API (positional args)
        try:
            _model = timesfm.TimesFm(
                context_len=CONTEXT_LEN,
                horizon_len=FORECAST_HORIZON,
                input_patch_len=32,
                output_patch_len=128,
                num_layers=20,
                model_dims=1280,
                backend="cpu",
            )
            _model.load_from_checkpoint(repo_id="google/timesfm-1.0-200m-pytorch")
            return _model
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass

    _model = None
    return None


# ---------------------------------------------------------------------------
# TimesFM Forecast Indicator
# ---------------------------------------------------------------------------

@register
class TimesFMForecast(BaseIndicator):
    """Zero-shot price forecast via Google's TimesFM foundation model.

    Feeds up to 512 bars of historical Close prices to TimesFM and obtains
    a point forecast for the next 10 trading days.  The predicted price
    change relative to the current price determines the signal direction,
    and the magnitude normalised by recent volatility sets the confidence.

    For backtesting efficiency, forecasts are computed every 10 bars and
    forward-filled in between (a forecast doesn't change intra-horizon).
    Batch inference is used when possible for speed.

    Requires ``pip install timesfm torch``.
    Falls back to HOLD with zero confidence if not installed.
    """

    MIN_CONTEXT = 30  # minimum bars for a meaningful forecast

    @property
    def name(self) -> str:
        return "TimesFM Forecast"

    @property
    def category(self) -> str:
        return "forecast"

    @property
    def lookback(self) -> int:
        return max(self.MIN_CONTEXT, 60)

    def supports_backtest_horizon(self, horizon_days: int) -> bool:
        return horizon_days == FORECAST_HORIZON

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        n = len(df)

        df["TFM_forecast"] = np.nan
        df["TFM_change_pct"] = np.nan

        model = _get_model()
        if model is None or n < self.MIN_CONTEXT:
            return df

        prices = df["Close"].values

        # Determine which bars to forecast at
        step = max(FORECAST_STEP, 1)
        forecast_indices = list(range(self.MIN_CONTEXT, n, step))
        # Always include the last bar
        if not forecast_indices or forecast_indices[-1] != n - 1:
            forecast_indices.append(n - 1)

        # Build contexts for batch inference
        contexts = []
        valid_indices = []
        for i in forecast_indices:
            ctx = prices[max(0, i - CONTEXT_LEN + 1) : i + 1].astype(np.float32)
            if len(ctx) >= self.MIN_CONTEXT:
                contexts.append(ctx)
                valid_indices.append(i)

        if not contexts:
            return df

        # Run inference (batch first, individual fallback)
        point_forecasts = self._batch_forecast(model, contexts)
        if point_forecasts is None:
            point_forecasts = self._individual_forecast(model, contexts)

        if point_forecasts is None:
            return df

        # Write results into the DataFrame
        fc_col = df.columns.get_loc("TFM_forecast")
        cp_col = df.columns.get_loc("TFM_change_pct")

        for j, i in enumerate(valid_indices):
            if point_forecasts[j] is None:
                continue
            forecast_price = float(point_forecasts[j])
            current_price = float(prices[i])
            if current_price > 0:
                change_pct = (forecast_price - current_price) / current_price
            else:
                change_pct = 0.0
            df.iat[i, fc_col] = forecast_price
            df.iat[i, cp_col] = change_pct

        df["TFM_forecast"] = df["TFM_forecast"].ffill()
        df["TFM_change_pct"] = df["TFM_forecast"] / df["Close"] - 1.0

        return df

    @staticmethod
    def _batch_forecast(model, contexts: list[np.ndarray]) -> "list | None":
        """Try batch inference — returns list of endpoint prices or None."""
        try:
            point_forecasts, _ = model.forecast(contexts, freq=[0] * len(contexts))
            return [float(pf[-1]) for pf in point_forecasts]
        except Exception:
            return None

    @staticmethod
    def _individual_forecast(model, contexts: list[np.ndarray]) -> "list | None":
        """Fallback: run one forecast at a time."""
        results = []
        any_success = False
        for ctx in contexts:
            try:
                pf, _ = model.forecast([ctx], freq=[0])
                results.append(float(pf[0][-1]))
                any_success = True
            except Exception:
                results.append(None)
        return results if any_success else None

    # ------------------------------------------------------------------
    # Signal
    # ------------------------------------------------------------------

    def get_signal(self, df: pd.DataFrame, idx: int = -1) -> SignalResult:
        if "TFM_forecast" not in df.columns:
            df = self.compute(df)

        forecast = df["TFM_forecast"].iloc[idx]
        change_pct = df["TFM_change_pct"].iloc[idx]

        if pd.isna(forecast) or pd.isna(change_pct):
            return SignalResult(
                self.name, SignalDirection.HOLD, 0.0,
                "TimesFM unavailable (pip install timesfm torch)",
            )

        current = df["Close"].iloc[idx]

        # Normalise predicted change by recent realised volatility
        actual_idx = idx if idx >= 0 else len(df) + idx
        returns = df["Close"].iloc[: actual_idx + 1].pct_change().dropna()
        if len(returns) > 20:
            daily_vol = returns.iloc[-60:].std()
        else:
            daily_vol = 0.02  # conservative fallback

        horizon_vol = daily_vol * np.sqrt(FORECAST_HORIZON) if daily_vol > 0 else 0.02
        z_score = change_pct / horizon_vol if horizon_vol > 0 else 0.0

        # Sigmoid-like mapping of |z| to confidence (saturates at ~0.9)
        confidence = min(0.9, abs(z_score) / (1.0 + abs(z_score)))

        if change_pct > 0.005:  # > +0.5% predicted
            return SignalResult(
                self.name, SignalDirection.BUY, confidence,
                f"TimesFM predicts +{change_pct:.1%} over {FORECAST_HORIZON}d "
                f"(${current:.2f} -> ${forecast:.2f})",
            )
        if change_pct < -0.005:  # > -0.5% predicted
            return SignalResult(
                self.name, SignalDirection.SELL, confidence,
                f"TimesFM predicts {change_pct:.1%} over {FORECAST_HORIZON}d "
                f"(${current:.2f} -> ${forecast:.2f})",
            )

        return SignalResult(
            self.name, SignalDirection.HOLD, 0.1,
            f"TimesFM predicts flat ({change_pct:+.1%}) over {FORECAST_HORIZON}d",
        )

    # ------------------------------------------------------------------
    # Chart
    # ------------------------------------------------------------------

    def get_chart_config(self) -> dict[str, Any]:
        return {
            "overlay": False,
            "columns": ["TFM_change_pct"],
            "colors": {"TFM_change_pct": "#9C27B0"},
            "subplot_title": "TimesFM Forecast (%)",
        }
