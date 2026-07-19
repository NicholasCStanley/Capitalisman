"""Walk-forward backtesting engine."""

import pandas as pd

from backtesting.metrics import compute_metrics
from backtesting.report import BacktestReport, Trade
from config.settings import DEFAULT_COST_PER_TRADE_PCT, WARMUP_BUFFER
from data.fetcher import is_crypto_ticker
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
    cost_per_trade_pct: float = DEFAULT_COST_PER_TRADE_PCT,
    evaluation_start: pd.Timestamp | None = None,
) -> BacktestReport:
    """Run walk-forward backtest.

    Args:
        df: Full OHLCV DataFrame (must include warmup period).
        indicators: dict of indicator name -> instance.
        ticker: Ticker symbol for the report.
        period: Data period string for the report.
        horizon_days: How many days forward to measure outcome.
        initial_capital: Starting capital.
        cost_per_trade_pct: Round-trip transaction cost as a percentage
            (slippage + commission). Deducted from each trade's PnL.

    Returns:
        BacktestReport with all trades and computed metrics.
    """
    report = BacktestReport(
        ticker=ticker,
        period=period,
        horizon_days=horizon_days,
        initial_capital=initial_capital,
        is_crypto=is_crypto_ticker(ticker),
        evaluation_start=evaluation_start,
        evaluation_end=df.index[-1] if not df.empty else None,
    )

    safe_indicators = {
        name: indicator for name, indicator in indicators.items()
        if indicator.backtest_safe
        and indicator.supports_backtest_horizon(horizon_days)
    }
    report.excluded_indicators = [
        name for name, indicator in indicators.items()
        if not indicator.backtest_safe
        or not indicator.supports_backtest_horizon(horizon_days)
    ]
    if not safe_indicators or df.empty:
        return report

    # Pre-compute indicators that explicitly declare point-in-time safety.
    # Their value at bar t must be identical whether computed on data[:t+1]
    # or on the full series.
    computed_df = df.copy()
    for name, indicator in safe_indicators.items():
        computed_df = indicator.compute(computed_df)

    # Determine warmup: max lookback + buffer
    max_lookback = max(ind.lookback for ind in safe_indicators.values())
    warmup = max_lookback + WARMUP_BUFFER

    if evaluation_start is not None:
        evaluation_position = int(computed_df.index.searchsorted(evaluation_start, side="left"))
    else:
        evaluation_position = 0

    if warmup >= len(computed_df) - horizon_days - 1:
        return report  # not enough data

    # Walk through test range
    test_start = max(warmup, evaluation_position - 1)
    test_end = len(computed_df) - horizon_days - 1

    t = test_start
    while t < test_end:
        # Read pre-computed indicator values at bar t (causal, no look-ahead)
        signal = combine_signals(safe_indicators, computed_df, horizon_days, idx=t,
                                 precomputed=True)

        if signal.direction == SignalDirection.HOLD:
            t += 1
            continue

        entry_idx = t + 1
        exit_idx = entry_idx + horizon_days
        entry_price = computed_df["Open"].iloc[entry_idx]
        exit_price = computed_df["Close"].iloc[exit_idx]
        entry_date = computed_df.index[entry_idx]
        exit_date = computed_df.index[exit_idx]

        actual_change = exit_price - entry_price
        if actual_change > 0:
            actual_direction = "BUY"
        elif actual_change < 0:
            actual_direction = "SELL"
        else:
            actual_direction = "HOLD"  # flat — neither direction is correct
        predicted_direction = signal.direction.value

        correct = predicted_direction == actual_direction

        # PnL: if we predicted BUY, gain is (exit-entry)/entry
        # if we predicted SELL, gain is (entry-exit)/entry
        # Transaction cost is deducted as a round-trip percentage.
        if predicted_direction == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price
        pnl_pct -= cost_per_trade_pct / 100.0

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
        t = exit_idx
        continue

    report = compute_metrics(report)
    return report
