# Capitalisman Improvement Plan

## Purpose

This document consolidates the verified findings from the July 2026 repository
review into one implementation plan. It separates reproduced correctness
defects from architectural improvements and product research ideas.

The immediate conclusion is that the simulation package has a strong causal and
auditable foundation, but the percentage-return backtester and signal scorer
need correctness work before their financial outputs should be treated as
reliable.

## Evidence summary

The following behaviors were reproduced against commit `9016c41`:

- OBV confidence at the same historical bar changed when future rows were
  present. In one synthetic probe, confidence was `0.3530` on data truncated at
  the evaluated bar and `0.0609` on the complete frame.
- `SignalResult(..., confidence=float("nan"))` produced confidence `1.0`.
- A single BUY score of `1e-12` produced BUY with 100% directional agreement.
- Returns of `-200%` followed by `-50%` produced an equity path of
  `$10,000 -> -$10,000 -> -$5,000`.
- A compounded sequence of `+100%` followed by `-50%` finished at its starting
  equity but reported profit factor `2.0` rather than dollar-ledger profit
  factor `1.0`.
- TimesFM made two extra inferences for the 1/5/20-bar cards when the primary
  horizon was five bars, and three when the primary horizon was outside those
  card horizons.
- Bubble Risk took approximately 3.76 seconds for 1,250 synthetic bars.
- The complete suite passed with Streamlit 1.60 (`238 passed`) but the simulator
  AppTest failed with the declared minimum Streamlit 1.28. The test result is
  dependency-version-sensitive.

## Priority 0: stop invalid or misleading results

### 1. Make historical indicator signals causal

**Problem**

`OBV.get_signal` normalizes divergence confidence over a slice that continues
through the end of the full DataFrame. Future volume can therefore alter a
historical signal's confidence.

Several crossover indicators also calculate a previous position with negative
index arithmetic. At `idx == 0`, that can wrap around to the final row.

**Proposed fix**

- Add one shared position-normalization helper to `BaseIndicator`.
- Reject out-of-range positions.
- Require each indicator to declare its required signal lookback.
- Bound every historical slice at `position + 1`.
- Return an explicit insufficient-history HOLD before accessing a previous row.

**Regression gate**

For every indicator declared historically safe, compare computation and signal
output at bar `t` between:

1. The complete frame evaluated at `idx=t`.
2. The same frame truncated through `t`, evaluated at `idx=-1`.

Compare declared indicator output columns, direction, confidence, and detail
using appropriate numeric tolerances. Inject external reference data so the
test is deterministic and does not depend on network access.

### 2. Reject non-finite values at model boundaries

**Problem**

The current clamp in `SignalResult` promotes NaN and positive infinity to
maximum confidence. Other public models accept non-finite scores, prices,
returns, and costs.

**Proposed fix**

- Validate with `math.isfinite` before clamping confidence.
- Add equivalent validation to `CombinedSignal`, strategy weights, forecast
  outputs, trades, portfolio snapshots, and metrics.
- Treat an invalid indicator result as a structured indicator failure, not a
  strong signal and not an indistinguishable market HOLD.

**Regression gate**

No NaN or infinity may enter a combined score, order, trade, metric, equity
snapshot, or exported artifact.

### 3. Separate directional agreement from evidence strength

**Problem**

The scorer divides the winning directional score by only BUY plus SELL evidence.
Numerical dust or one extremely weak indicator can therefore produce an
actionable result with 100% agreement.

An exact BUY/SELL tie is also biased toward BUY when the ambiguity threshold is
set to the allowed value `0.0`.

**Proposed fix**

Introduce an explicit immutable scoring policy containing:

- Indicator weights.
- Timescale adjustments.
- Ambiguity threshold.
- Minimum normalized evidence strength.
- Optional strategy-specific minimum number of actionable indicators.

Always return HOLD for exact ties. Report these concepts separately:

- Directional agreement: how one-sided the actionable evidence is.
- Evidence strength: credible score relative to the maximum attainable score
  for the selected policy.

A universal quorum should not be imposed because single-indicator strategies
are a supported use case.

**Regression gate**

- Negligible evidence cannot produce BUY or SELL.
- Equal BUY and SELL evidence always produces HOLD.
- A single-indicator strategy can act when it clears its explicit evidence
  policy.

### 4. Make historical safety opt-in and executable

**Problem**

`BaseIndicator.backtest_safe` defaults to `True`. A new indicator is trusted
without demonstrating that its transform, data source, or signal extraction is
point-in-time safe.

**Proposed fix**

- Default historical safety to `False`.
- Require explicit opt-in.
- Fail CI when an opted-in indicator violates causal-conformance tests.
- Distinguish causal computation from point-in-time source guarantees. A
  backward-looking transform over revised data is not necessarily
  point-in-time safe.
- Consider replacing the single boolean with declared capabilities such as:
  `causal_transform`, `point_in_time_source`, `deterministic`, and supported
  horizons.

### 5. Validate market data before indicator computation

**Problem**

The backtester performs little input validation. The simulator validates only
Open and Close, and the UI prepares strategy signals before constructing the
engine, so invalid High, Low, or Volume data can reach indicators first.

**Proposed fix**

Create one validated market-data boundary used before prediction, strategy
preparation, simulation, and backtesting. At minimum validate:

- Required columns and numeric types.
- Finite, positive Open/High/Low/Close values.
- Finite, non-negative Volume.
- `High >= max(Open, Close, Low)`.
- `Low <= min(Open, Close, High)`.
- Datetime index, sorted and unique timestamps, timezone policy, and freshness.
- Supported interval regularity and documented handling of missing bars.

Engine public APIs should validate configuration independently:

- Positive finite capital.
- Positive integer horizon.
- Finite supported transaction costs.
- Valid evaluation bounds.

### 6. Replace percentage-only backtest accounting

**Problem**

The backtester creates isolated percentage returns and later compounds them. It
can continue reporting trades after equity becomes negative, calculate
drawdowns above 100%, and calculate profit factor from incomparable percentage
bases. Its trade-return Sharpe approximation is not a daily marked-to-market
portfolio Sharpe.

**Proposed fix**

Use an explicit portfolio ledger containing:

- Cash and position quantity.
- Entry and current notional.
- Realized and unrealized dollar P&L.
- Per-fill fees.
- Mark-to-market equity.
- Collateral, margin, borrow cost, and liquidation state when shorting is
  supported.

Until a short collateral model exists, either disable short execution or report
SELL predictions as directional-accuracy observations without modeling a short
portfolio. Do not open trades after liquidation.

Calculate cumulative return, drawdown, Sharpe, and profit factor from the
portfolio equity and dollar-P&L ledger.

## Priority 1: model and simulation consistency

### 7. Use one pure scorer with explicit policies

**Problem**

Prediction/backtesting and simulation independently implement the same weighted
direction mechanism. There are two scorers, and their policy sources differ:
session overrides for prediction versus immutable strategy definitions for
simulation.

**Proposed fix**

Extract one pure scorer that consumes already-produced `SignalResult` values and
an explicit `ScoringPolicy`. Keep policy construction separate:

- Prediction/backtesting can construct a session policy.
- Simulation can construct an immutable strategy policy.

This preserves intentional policy differences while centralizing validation,
ties, evidence thresholds, timescale adjustments, and confidence semantics.

### 8. Make TimesFM inference explicit, reusable, and cost-aware

**Problem**

The multi-timeframe display can run full model inference repeatedly. Forecast
artifacts are stored on mutable indicator attributes, making result ownership
and display behavior call-order-dependent.

BUY eligibility uses `P(return > default cost)`, while SELL eligibility uses
`P(down)` plus a median-return threshold. Neither side consistently uses the
user-selected effective cost.

**Proposed fix**

- Return forecast artifacts to the caller instead of storing result state on
  the indicator.
- Cache artifacts by data fingerprint, model/runtime configuration, origin, and
  horizon.
- Explicitly compute the requested 1/5/20-bar horizons once, or omit forecast
  indicators from cards without a matching cached artifact.
- Pass effective costs through the forecast/scoring policy.
- Use symmetric probabilities:
  - BUY: `P(return > +cost)`.
  - SELL: `P(return < -cost)`.
- Treat quantile-interpolated tail probabilities as approximations and avoid
  presenting q10/q90 extrapolation as calibrated 0% or 100% certainty.

### 9. Correct simulation boundary behavior

**Problem**

When a Buy & Hold replay begins at the first available bar, it cannot use a
previous close to queue an order. It therefore buys at the second open despite
the UI promising the first eligible open.

Completed or goal-stopped simulations may also retain an open position. Their
reported equity is mark-to-market equity, not liquidation value, and excludes a
future exit fee.

**Proposed fix**

- Treat Buy & Hold as an explicit initial-allocation instruction that can fill
  at the first replay open without requiring a prior market signal.
- Preserve the next-open invariant for signal-driven strategies.
- Report both mark-to-market equity and net liquidation value, or explicitly
  liquidate at configured terminal boundaries.
- Ensure goal semantics specify whether the target is marked-to-market or
  realizable after liquidation costs.

## Priority 2: reliability and reproducibility

### 10. Isolate indicator failures

Run each indicator through an outcome boundary that records either a valid
result or a structured error. Continue displaying valid indicators, but do not
silently convert infrastructure failures into neutral market evidence.

### 11. Consolidate cache behavior

Replace indefinite module dictionaries with one bounded cache policy:

- Success TTL.
- Shorter failure TTL.
- Size limit and explicit invalidation.
- Provider-, credential-, and configuration-aware keys.
- Observable hit, miss, stale, and failure states.

Do not cache missing FRED credentials or transient provider failures for the
entire server lifetime.

### 12. Scope TimesFM runtime ownership

The current TimesFM runtime is a process-global singleton. In multi-session
deployment, one session can replace another session's profile or workload
configuration.

Make runtime ownership explicit. Depending on the intended deployment, use a
configuration-keyed resource cache with concurrency controls or a
session/request-owned runtime service. Avoid uncontrolled duplicate model loads
on limited GPU memory.

### 13. Make persistence match the deployment model

For the documented personal/local application:

- Validate watchlist names and ticker element types.
- Bound list sizes.
- Use a lock and atomic temporary-file replacement.

If multi-user deployment becomes a product requirement, move watchlists to
authenticated transactional storage. Multi-user database work is not an
immediate requirement for the current personal research scope.

### 14. Add reproducible dependency and CI controls

- Add a lock or tested constraints file for the supported environment.
- Test both the minimum supported dependency set and the locked set.
- Run pytest, formatting/linting, type checking, and dependency auditing in CI.
- Keep TimesFM/CUDA dependencies isolated.
- Add an optional GPU contract matrix without downloading model weights in
  ordinary CI.

The Streamlit 1.28 versus 1.60 AppTest result demonstrates why both minimum and
locked dependency tests are necessary.

Remove or repair tests whose assertions cannot fail. In particular, the
different-horizon combiner test currently ends its main assertion with
`or True`.

### 15. Export reproducible research artifacts

Backtest exports should include, or reference through a manifest:

- Data fingerprint and provider metadata.
- Evaluation timestamps and interval.
- Indicator names and versions.
- Effective weights, thresholds, and horizon.
- Transaction costs and execution policy.
- Software revision and dependency environment.
- Trade ledger and portfolio equity ledger.

## Priority 3: research quality and product usefulness

### 16. Treat corporate actions as an accounting and reproducibility problem

`yfinance` auto-adjusts OHLC by default, and adjusted history may change as
corporate actions are incorporated. This does not automatically mean that a
future split leaks predictive information into every earlier percentage return:
uniform rescaling can leave returns and scale-invariant indicators unchanged.

Do not switch to raw prices alone; unmodeled split gaps can create worse
signals. Instead:

- Store immutable timestamped market-data snapshots.
- Preserve raw prices, adjustment factors, dividends, and splits.
- Define whether each result represents price return or total return.
- Apply corporate actions through the portfolio ledger.
- Add delisting, halt, and survivorship-bias policy as the research scope grows.

### 17. Use point-in-time macro vintages

A publication lag prevents use before initial release but does not prevent
revision look-ahead. FRED indicators should remain excluded from historical
claims until the pipeline uses point-in-time ALFRED vintages or another
revision-aware source.

### 18. Calibrate probabilities only after correctness work

Directional agreement is not probability of success. Once causal data,
execution, and accounting are reliable, treat indicator results as features and
evaluate a probability-of-net-profit model with strict walk-forward splits.

Report:

- Probability of net profit after costs.
- Reliability/calibration diagrams.
- Brier score and log loss.
- Sample count and dependence-aware uncertainty intervals.
- Results by asset class, horizon, and market regime.
- Comparisons with simple technical, random-walk, seasonal, and Buy & Hold
  baselines.

Weight fitting, model selection, and calibration must not use the final
reporting interval.

## Performance work

Performance improvements should follow correctness:

1. Add repeatable benchmarks for every indicator and a representative
   multi-ticker scan.
2. Stride slow-moving structural computations only after measuring the signal
   impact of forward filling.
3. Vectorize Bubble Risk's repeated R/S work and polynomial fitting, with parity
   tests against the reference implementation.
4. Optimize systemic correlation using a benchmark-backed algorithm; do not
   assume a simple rank-one or warm-started eigendecomposition without proving
   numerical equivalence.
5. Batch provider downloads and TimesFM inference. Avoid blind ticker-level
   parallelism that can amplify provider rate limits or GPU memory use.

## Required regression invariants

1. Adding future bars cannot change a historically safe indicator's value or
   signal at an earlier bar.
2. No non-finite value can enter scoring, execution, metrics, or exports.
3. Negligible evidence and exact directional ties produce HOLD.
4. Every fill occurs after its signal information became available, except an
   explicitly configured initial allocation such as Buy & Hold.
5. Portfolio equity cannot become negative without an explicit margin and
   liquidation model.
6. No order opens after liquidation or completion.
7. Profit factor reconciles to dollar P&L.
8. Batch replay and repeated single-step replay remain identical.
9. Prediction, backtesting, and simulation produce the same score when given
   identical signals and policy.
10. Configured transaction cost changes eligibility, fills, liquidation value,
    and reporting consistently.
11. Minimum-supported and locked dependency environments both pass CI.
12. Exported results contain enough configuration and data identity to reproduce
    the run.

## Recommended delivery order

### Phase 1: correctness

1. Fix OBV and historical index normalization.
2. Add finite-value validation.
3. Fix tie behavior and add normalized evidence strength.
4. Make historical safety opt-in and add causal-conformance tests.
5. Add pre-computation market-data validation.
6. Replace backtest percentage accounting with a portfolio ledger.

### Phase 2: consistency

1. Extract the pure scorer and explicit policies.
2. Make TimesFM artifacts reusable and costs symmetric.
3. Correct Buy & Hold first-open behavior and terminal-value semantics.
4. Isolate indicator failures and consolidate caches.

### Phase 3: safety net and reproducibility

1. Add locked/minimum dependency CI matrices.
2. Repair ineffective tests and expand accounting/property tests.
3. Add configuration, data, and software fingerprints to exports.
4. Make local persistence atomic and runtime ownership explicit.

### Phase 4: research and performance

1. Establish point-in-time market and macro data artifacts.
2. Add calibration and baseline evaluation.
3. Optimize measured indicator and screening bottlenecks.
4. Expand execution assumptions, position sizing, and portfolio support only
   when their accounting can remain auditable.

## Architecture target

```text
Validated, fingerprinted point-in-time market data
                    |
                    v
        Causal indicator outcomes or errors
                    |
                    v
       Finite SignalResult feature values
                    |
                    v
        One pure scorer + ScoringPolicy
                    |
                    v
       Shared portfolio/fill/accounting core
                    |
          +---------+---------+
          |                   |
          v                   v
 Auditable backtest     Interactive replay
 report and export      and event ledger
```

The existing simulation package provides much of the desired execution,
fingerprinting, and event-ledger pattern. It should be extended into shared
infrastructure rather than rewritten.
