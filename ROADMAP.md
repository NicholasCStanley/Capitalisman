# Capitalisman Development Roadmap

This document reserves and organizes ideas for future development. Items here
are proposals, not commitments, and are not implemented unless explicitly
marked complete.

## Product Direction

Evolve Capitalisman from an indicator dashboard into a repeatable research
workflow that explains:

- What the current signal suggests.
- How strongly the underlying evidence agrees.
- How similar signals performed historically.
- Which market conditions support or weaken the result.
- What uncertainty and downside remain.

## Near-Term Priorities

### Signal Interpretation

- [ ] Add a signed contribution chart for every indicator.
- [ ] Separate directional agreement, historical reliability, and expected move.
- [ ] Summarize conflicting indicator groups in plain language.
- [ ] Add approachable explanations for backtest metrics and assumptions.
- [ ] Display data freshness, missing data, and unavailable indicators.
- [ ] Expose the exact weights, thresholds, and configuration behind each result.

### Strategy Workflows

- [ ] Introduce a formal strategy configuration model.
- [ ] Add presets such as Conservative Trend, Short-Term Momentum, Macro Risk,
      and Crypto 24/7.
- [ ] Allow named strategies to be saved, duplicated, edited, and restored.
- [ ] Keep ticker, period, horizon, and strategy synchronized between pages.
- [ ] Add a guided first-run workflow for less experienced users.
- [ ] Export complete research reports in addition to raw CSV files.

## Research Quality

### Historical Calibration

- [ ] Measure hit rate, median return, and downside for comparable past signals.
- [ ] Show expected-return distributions and confidence intervals.
- [ ] Compare results against buy-and-hold, simple technical baselines, and
      random-direction baselines.
- [ ] Report whether observed performance is statistically meaningful.

### Out-of-Sample Validation

- [ ] Add explicit training, validation, and test date ranges.
- [ ] Add rolling walk-forward evaluation.
- [ ] Prevent thresholds or weights selected on one period from being evaluated
      as though they were chosen independently on that same period.
- [ ] Add parameter-sensitivity charts to reveal fragile configurations.
- [ ] Store reproducible configuration identifiers with every backtest.

### Regime Analysis

- [ ] Classify trend, volatility, liquidity, and macro regimes.
- [ ] Break down performance by regime.
- [ ] Warn when a strategy is being used outside its historically favorable
      conditions.
- [ ] Support regime-dependent weights or strategy selection.

## Decision Support

- [ ] Add volatility and ATR context to each signal.
- [ ] Add research-oriented invalidation levels and risk ranges.
- [ ] Add volatility-based position-sizing examples with prominent caveats.
- [ ] Support user-selected benchmarks instead of always using SPY.
- [ ] Add alerts for signal changes, agreement thresholds, volatility spikes,
      and indicator crossovers.
- [ ] Add a watchlist dashboard showing changes since the previous scan.

## Portfolio Research

- [ ] Backtest multiple assets and simultaneous positions.
- [ ] Model cash allocation, position limits, and maximum portfolio exposure.
- [ ] Add configurable rebalancing and position-sizing rules.
- [ ] Model stop-loss, take-profit, and trailing-exit rules.
- [ ] Account for short borrow costs and asset-specific execution assumptions.
- [ ] Report portfolio-level volatility, drawdown, concentration, and turnover.

## Technical Foundation

- [ ] Separate the research engine from Streamlit-specific caching and state.
- [ ] Support CLI, scheduled-job, and API entry points.
- [ ] Add a market-data provider abstraction rather than relying on one source.
- [ ] Add formal data validation, freshness checks, and provider diagnostics.
- [ ] Persist strategies and research results in SQLite or Parquet.
- [ ] Add vectorized or batch backtesting for screeners and parameter grids.
- [ ] Add UI integration tests for navigation, saved strategies, reset behavior,
      and stale-state prevention.
- [ ] Add performance benchmarks for indicator computation and watchlist scans.

## Suggested Delivery Order

1. Signal contribution visualization and strategy presets.
2. Saved and versioned strategy configurations.
3. Out-of-sample and rolling walk-forward testing.
4. Historical calibration and expected-return distributions.
5. Regime breakdowns and parameter-sensitivity analysis.
6. Portfolio backtesting and alerts.

## Guiding Principle

Capitalisman should not merely provide a signal. It should show when similar
signals worked, how robust the evidence is, what could invalidate the result,
and how much uncertainty remains.

