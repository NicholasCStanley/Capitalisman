"""Weighted majority voting signal combiner."""

import pandas as pd

from config.settings import (
    AMBIGUITY_THRESHOLD,
    INDICATOR_CATEGORIES,
    INDICATOR_WEIGHTS,
    TIMESCALE_ADJUSTMENTS,
)
from indicators.base import BaseIndicator
from signals.base import CombinedSignal, SignalDirection, SignalResult


def _get_timescale(horizon_days: int) -> str:
    if horizon_days <= 3:
        return "short"
    elif horizon_days <= 10:
        return "medium"
    return "long"


def _get_adjusted_weight(indicator_name: str, horizon_days: int) -> float:
    base_weight = INDICATOR_WEIGHTS.get(indicator_name, 1.0)
    category = INDICATOR_CATEGORIES.get(indicator_name, "trend")
    timescale = _get_timescale(horizon_days)
    adjustment = TIMESCALE_ADJUSTMENTS[timescale].get(category, 1.0)
    return base_weight * adjustment


def combine_signals(
    indicators: dict[str, BaseIndicator],
    df: pd.DataFrame,
    horizon_days: int = 5,
    idx: int = -1,
    precomputed: bool = False,
) -> CombinedSignal:
    """Combine signals from multiple indicators using weighted voting.

    Args:
        indicators: dict of name -> BaseIndicator instance
        df: DataFrame with OHLCV data (indicator columns will be computed as needed)
        horizon_days: prediction horizon for timescale adjustment
        idx: bar index to evaluate
        precomputed: if True, skip indicator computation (columns already in df)

    Returns:
        CombinedSignal with combined direction, confidence, and breakdown.
    """
    individual_signals: list[SignalResult] = []
    direction_scores: dict[str, float] = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

    for name, indicator in indicators.items():
        if not precomputed:
            df = indicator.compute(df)
        signal = indicator.get_signal(df, idx=idx)
        individual_signals.append(signal)

        weight = _get_adjusted_weight(name, horizon_days)
        score = signal.confidence * weight
        direction_scores[signal.direction.value] += score

    # Determine winner
    sorted_dirs = sorted(direction_scores.items(), key=lambda x: x[1], reverse=True)
    top_dir, top_score = sorted_dirs[0]
    second_dir, second_score = sorted_dirs[1]

    total_score = sum(direction_scores.values())

    # If scores are too close, signal is ambiguous -> HOLD
    if total_score > 0 and (top_score - second_score) / total_score < AMBIGUITY_THRESHOLD:
        confidence = 0.0
        direction = SignalDirection.HOLD
        reasoning = (
            f"Ambiguous: {top_dir} ({top_score:.2f}) vs "
            f"{second_dir} ({second_score:.2f}) — too close to call"
        )
    else:
        direction = SignalDirection(top_dir)
        confidence = top_score / total_score if total_score > 0 else 0.0
        reasoning = f"{top_dir} wins with score {top_score:.2f}/{total_score:.2f}"

    return CombinedSignal(
        direction=direction,
        confidence=confidence,
        scores=direction_scores,
        individual_signals=individual_signals,
        reasoning=reasoning,
    )
