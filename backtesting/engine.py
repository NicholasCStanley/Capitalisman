"""Walk-forward backtesting engine."""

import pandas as pd

from backtesting.metrics import compute_metrics
from backtesting.report import BacktestReport, Trade
from config.settings import WARMUP_BUFFER
from indicators.base import BaseIndicator
from signals.base import SignalDirection
from signals.combiner import combine_signals


def run_backtest(
    df: pd.DataFrame,
    indicators: dict[str, BaseIndicator],
    ticker: str,
    period: str,
    horizon_days: int = 5,
    initial_capital: float = 10_000.0,
) -> BacktestReport:
    """Run walk-forward backtest.

    Args:
        df: Full OHLCV DataFrame (must include warmup period).
        indicators: dict of indicator name -> instance.
        ticker: Ticker symbol for the report.
        period: Data period string for the report.
        horizon_days: How many days forward to measure outcome.
        initial_capital: Starting capital.

    Returns:
        BacktestReport with all trades and computed metrics.
    """
    report = BacktestReport(
        ticker=ticker,
        period=period,
        horizon_days=horizon_days,
        initial_capital=initial_capital,
    )

    # Pre-compute all indicators once over the full dataset.
    # All indicators used here (SMA, EMA, MACD, ADX, RSI, Stochastic, BB,
    # VWAP, OBV) are causal — they use only rolling/cumulative operations,
    # so the value at bar t is identical whether computed on data[:t+1] or
    # on the full series. This lets us compute once and index by position.
    computed_df = df.copy()
    for name, indicator in indicators.items():
        computed_df = indicator.compute(computed_df)

    # Determine warmup: max lookback + buffer
    max_lookback = max(ind.lookback for ind in indicators.values())
    warmup = max_lookback + WARMUP_BUFFER

    if warmup >= len(computed_df) - horizon_days:
        return report  # not enough data

    # Walk through test range
    test_start = warmup
    test_end = len(computed_df) - horizon_days

    t = test_start
    while t < test_end:
        # Read pre-computed indicator values at bar t (causal, no look-ahead)
        signal = combine_signals(indicators, computed_df, horizon_days, idx=t,
                                 precomputed=True)

        if signal.direction == SignalDirection.HOLD:
            t += 1
            continue

        entry_price = computed_df["Close"].iloc[t]
        exit_price = computed_df["Close"].iloc[t + horizon_days]
        entry_date = computed_df.index[t]
        exit_date = computed_df.index[t + horizon_days]

        actual_change = exit_price - entry_price
        actual_direction = "BUY" if actual_change > 0 else "SELL"
        predicted_direction = signal.direction.value

        correct = predicted_direction == actual_direction

        # PnL: if we predicted BUY, gain is (exit-entry)/entry
        # if we predicted SELL, gain is (entry-exit)/entry
        if predicted_direction == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        trade = Trade(
            entry_date=entry_date,
            exit_date=exit_date,
            direction=predicted_direction,
            entry_price=entry_price,
            exit_price=exit_price,
            predicted_direction=predicted_direction,
            actual_direction=actual_direction,
            correct=correct,
            pnl_pct=pnl_pct,
        )
        report.trades.append(trade)

        # Skip forward to avoid overlapping trades
        t += horizon_days
        continue

    report = compute_metrics(report)
    return report
