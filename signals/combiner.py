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

    working_df = df if precomputed else df.copy()

    for name, indicator in indicators.items():
        if not precomputed:
            working_df = indicator.compute(working_df)
        signal = indicator.get_signal(working_df, idx=idx)
        individual_signals.append(signal)

        weight = _get_adjusted_weight(name, horizon_days)
        score = signal.confidence * weight
        # HOLD signals are recorded for display but don't participate in
        # directional voting — they represent absence of a signal, not a
        # competing direction.
        direction_scores[signal.direction.value] += score

    # Only BUY and SELL compete; HOLD is the fallback when neither wins
    buy_score = direction_scores["BUY"]
    sell_score = direction_scores["SELL"]
    directional_total = buy_score + sell_score

    if directional_total == 0:
        return CombinedSignal(
            direction=SignalDirection.HOLD,
            confidence=0.0,
            scores=direction_scores,
            individual_signals=individual_signals,
            reasoning="No actionable signals from any indicator",
        )

    top_dir, top_score = ("BUY", buy_score) if buy_score >= sell_score else ("SELL", sell_score)
    second_score = sell_score if top_dir == "BUY" else buy_score

    # If BUY and SELL scores are too close, signal is ambiguous -> HOLD
    if (top_score - second_score) / directional_total < AMBIGUITY_THRESHOLD:
        confidence = 0.0
        direction = SignalDirection.HOLD
        reasoning = (
            f"Ambiguous: BUY ({buy_score:.2f}) vs "
            f"SELL ({sell_score:.2f}) — too close to call"
        )
    else:
        direction = SignalDirection(top_dir)
        confidence = top_score / directional_total
        reasoning = f"{top_dir} wins with score {top_score:.2f}/{directional_total:.2f}"

    return CombinedSignal(
        direction=direction,
        confidence=confidence,
        scores=direction_scores,
        individual_signals=individual_signals,
        reasoning=reasoning,
    )
