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

### TimesFM Foundation — Completed

- [x] Isolate PyTorch, CUDA, and TimesFM dependencies in a dedicated Conda
      environment that ignores user-site packages.
- [x] Replace the legacy TimesFM wrapper with the official TimesFM 2.5 PyTorch
      runtime, lazy model loading, hardware preflight, and actionable failures.
- [x] Make forecasts honor the user-selected horizon throughout prediction,
      comparison, screening, and backtesting.
- [x] Expose point, q10, q50, and q90 paths plus cost-aware directional
      probabilities in the Predict interface.
- [x] Add leakage-resistant rolling evaluation with naïve-baseline MAE,
      directional accuracy, interval coverage, Brier score, and pinball loss.
- [x] Validate the test suite and real inference on an NVIDIA CUDA device.

### TimesFM Forecast Development

#### Phase 1 — Establish Measurable Value

- [ ] Add drift, moving-average, exponential-smoothing, and simple autoregressive
      baselines alongside the existing last-price baseline.
- [ ] Run reproducible multi-asset benchmark suites across equities, indices,
      rates, commodities, and crypto.
- [ ] Evaluate multiple forecast horizons and minimum-context lengths without
      selecting settings on the final test period.
- [ ] Store benchmark inputs, model/package versions, configuration, metrics, and
      per-origin results as versioned research artifacts.
- [ ] Add a benchmark results page that clearly shows whether TimesFM beats each
      baseline and where it fails.
- [ ] Define minimum acceptance criteria before increasing TimesFM's voting weight
      or presenting it as more than experimental.

#### Phase 2 — Calibration and Regime Awareness

- [ ] Add chronological train/calibration/test partitions and nested rolling
      evaluation for any learned thresholds.
- [ ] Measure reliability curves for `P(up)` and empirical coverage for every
      forecast interval.
- [ ] Calibrate probabilities and quantiles on held-out data using isotonic,
      conformal, or other appropriate post-processing methods.
- [ ] Break down accuracy and calibration by volatility, trend, liquidity, asset
      class, and macro regime.
- [ ] Detect distribution shift and warn when the current context is unlike the
      model's validated operating conditions.
- [ ] Make signal confidence depend on calibrated historical reliability rather
      than raw model probability alone.

#### Phase 3 — Stronger Local ML

- [ ] Compare raw price, log-price, return, volatility-scaled return, and
      detrended input representations using identical evaluation windows.
- [ ] Add covariate experiments for volume, realized volatility, market returns,
      rates, and regime features without introducing future leakage.
- [ ] Build a local PyTorch ensemble that learns when to use TimesFM versus
      statistical and technical baselines.
- [ ] Investigate parameter-efficient fine-tuning only after the zero-shot
      benchmark and data-splitting framework are stable.
- [ ] Add mixed-precision inference, safe batch sizing, model caching, and runtime
      telemetry for supported NVIDIA hardware.
- [ ] Track model lineage, data lineage, random seeds, and reproducibility metadata
      for every trained or calibrated artifact.

#### Phase 4 — Forecast User Experience

- [ ] Visualize historical forecast cones against realized prices so users can
      see calibration rather than only the latest path.
- [ ] Explain in plain language when TimesFM agrees with, contradicts, or adds no
      value beyond simpler indicators.
- [ ] Show baseline comparisons, sample size, regime, data freshness, and model
      status beside every forecast.
- [ ] Let users select Auto, CUDA, or CPU and inspect model/cache information from
      the interface.
- [ ] Provide cancellable progress, estimated workload, and bounded benchmark
      presets for expensive local analysis.
- [ ] Export a self-contained forecast research report with assumptions,
      uncertainty, metrics, and configuration.

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

1. Expand TimesFM baselines and multi-asset benchmark coverage.
2. Add benchmark persistence and an interpretable results view.
3. Add chronological calibration and regime breakdowns.
4. Add signal contribution visualization and strategy presets.
5. Add saved and versioned strategy configurations.
6. Evaluate local ensembles and parameter-efficient fine-tuning.
7. Add portfolio backtesting, research reports, and alerts.

## Guiding Principle

Capitalisman should not merely provide a signal. It should show when similar
signals worked, how robust the evidence is, what could invalidate the result,
and how much uncertainty remains.
