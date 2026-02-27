"""Backtest report dataclass."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Trade:
    """A single backtested trade."""

    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: str  # "BUY" or "SELL"
    entry_price: float
    exit_price: float
    predicted_direction: str
    actual_direction: str
    correct: bool
    pnl_pct: float  # percent return


@dataclass
class BacktestReport:
    """Complete backtest results."""

    ticker: str
    period: str
    horizon_days: int
    initial_capital: float
    trades: list[Trade] = field(default_factory=list)

    # Computed metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    cumulative_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0

    # Equity curve
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
