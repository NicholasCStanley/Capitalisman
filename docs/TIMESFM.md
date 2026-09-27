# TimesFM Research Runtime

Capitalisman treats TimesFM as an optional research component, not a guaranteed
trading oracle. The integration uses TimesFM 2.5's PyTorch API to produce a
point forecast and quantiles, converts those into cost-aware probabilities, and
keeps the model isolated from the core application environment.

## Safe Isolated Installation

Do not install or upgrade PyTorch in the base Conda environment. Create the
reserved environment first:

```bash
conda env create -f environment-timesfm.yml
conda run -n capitalisman-timesfm python -m pip install --upgrade pip
```

The environment sets `PYTHONNOUSERSITE=1` so packages installed in the user's
global Python directory cannot leak into this runtime.

This workstation's RTX 5090 and driver support a CUDA 12.8 PyTorch wheel. Install
that wheel inside the new environment, then install the app and TimesFM packages:

```bash
conda run -n capitalisman-timesfm python -m pip install \
  torch --index-url https://download.pytorch.org/whl/cu128
conda run -n capitalisman-timesfm python -m pip install -r requirements-timesfm.txt
```

On a different machine, use the command produced by the official PyTorch
installer selector instead of assuming `cu128`. CUDA toolkit packages installed
system-wide are not modified by these commands; PyTorch's runtime stays inside
the Conda environment.

## Runtime Check

First run the dependency and hardware preflight, which does not load weights:

```bash
conda run -n capitalisman-timesfm python -m scripts.timesfm_check --device cuda
```

Then run an explicit smoke test:

```bash
conda run -n capitalisman-timesfm python -m scripts.timesfm_check \
  --device cuda --smoke
```

The smoke test downloads the model on first use and caches it in the normal
Hugging Face cache. It prints point, 10th-, 50th-, and 90th-percentile paths.
The preflight reports the selected device, package versions, GPU, GPU memory,
available RAM, and free disk. Errors remain visible in the indicator rather than
silently masquerading as a valid neutral prediction.

The sidebar exposes Auto, CPU and CUDA independently of workload profiles. An
explicit CUDA request fails if CUDA is unavailable. CPU loading binds the model
instance before checkpoint transfer; it does not change `CUDA_VISIBLE_DEVICES`
or patch PyTorch's CUDA detection. All parameters and buffers, plus the input
device, are checked after loading and before inference. The `model_device`
status field reports this observation; preflight leaves it null. The adapter
is verified against TimesFM 2.0.2 and should be rechecked when upgrading it.

Changing the shared runtime configuration unloads the prior model. Calls on
one runtime are serialized against unload. Out-of-memory failures release its
model reference, clear available CUDA cache, and fail the whole request without
returning partial forecasts or automatically retrying. Reduce batch/chunk size
explicitly before retrying. `forecast(..., cancel_check=callback)` supports
cooperative cancellation before/after each chunk; it cannot stop a running GPU
kernel. The [suite runner](RESEARCH_WORKFLOW.md#bounded-suites-from-local-data)
uses worker processes for enforced timeouts and cancellation.

`timesfm_check --smoke` includes status after inference. Add `--no-torch-compile`
to skip optional Torch compilation during a small diagnostic. The Python config
exposes `torch_compile` (default true); suite defaults set it false. A cached,
uncompiled synthetic CPU → CUDA → CPU check passed on the RTX 5090 with a
32-bar context, five-bar horizon and batch/chunk size one. This verifies device
switching, not every profile or GPU configuration.

Optional runtime settings:

| Variable | Default | Purpose |
|---|---:|---|
| `CAPITALISMAN_TIMESFM_DEVICE` | `auto` | `auto`, `cuda`, or `cpu` |
| `CAPITALISMAN_TIMESFM_MODEL_ID` | `google/timesfm-2.5-200m-pytorch` | Model source |
| `CAPITALISMAN_TIMESFM_MAX_CONTEXT` | `1024` | Maximum input bars |
| `CAPITALISMAN_TIMESFM_FORECAST_CONTEXT` | `1024` | Selected input bars, bounded by maximum context |
| `CAPITALISMAN_TIMESFM_MAX_HORIZON` | `256` | Maximum output bars |
| `CAPITALISMAN_TIMESFM_BATCH_SIZE` | `32` | Compiled inference batch size |
| `CAPITALISMAN_TIMESFM_CHUNK_SIZE` | `32` | Maximum series sent to the model per call |
| `CAPITALISMAN_TIMESFM_MEMORY_TARGET` | `0.72` | Fraction of total VRAM allowed by empirical recommendations |
| `CAPITALISMAN_TIMESFM_PROFILE` | `custom` | Profile label recorded with results |
| `CAPITALISMAN_TIMESFM_USE_CASE` | `interactive` | Workload label recorded with results |

## Hardware and Workload Profiles

Capitalisman separates hardware utilization from predictive methodology. Runtime
profiles control context capacity, selected context, batch size, and workload
chunking. They do not change signal thresholds, indicator weights, target
representation, or probability calibration.

The application offers `Auto`, `Fast`, `Balanced`, and `Thorough` profiles when
TimesFM is selected. Selection uses currently free VRAM rather than relying only
on the GPU product name, then adapts to the workload:

| Use case | Behavior |
|---|---|
| `interactive` | Latest forecast with a single-series chunk |
| `watchlist` | Batched latest forecasts across assets |
| `backtest` | Bounded historical-origin batches |
| `research` | Larger context and batch envelope for benchmark sweeps |

The starting memory tiers are conservative: at least 24 GB free VRAM uses the
enthusiast tier, 14 GB the high tier, 10 GB the performance tier, and 7 GB the
standard tier. Lower-memory GPUs and CPUs receive reduced contexts and batches.
Because other applications may occupy VRAM, an RTX 5090 can intentionally select
a lower tier when little memory is free.

Balanced starting points for common dedicated GPUs are:

| Typical hardware | Free-VRAM tier | Interactive | Watchlist | Research |
|---|---|---|---|---|
| RTX 5090, about 32 GB free | Enthusiast | context 1024, batch 32, chunk 1 | context 1024, batch 256, chunk 128 | context 2048, batch 256, chunk 128 |
| RTX 5070 Ti, about 16 GB free | High | context 1024, batch 32, chunk 1 | context 1024, batch 128, chunk 128 | context 2048, batch 128, chunk 128 |
| RTX 5070, about 12 GB free | Performance | context 1024, batch 32, chunk 1 | context 1024, batch 64, chunk 128 | context 2048, batch 64, chunk 128 |
| 8 GB GPU | Standard | context 1024, batch 32, chunk 1 | context 1024, batch 64, chunk 128 | context 2048, batch 64, chunk 128 |

These are starting limits, not claims of superior predictive accuracy. `Fast`
halves the selected context and caps batches at 64. `Thorough` doubles the
selected context where feasible, reduces batch size, and raises the memory target
from 72% to 82%. The empirical probe should be used before sustained large runs.

Inspect the recommendation without loading weights:

```bash
conda run -n capitalisman-timesfm python -m scripts.timesfm_check \
  --profile balanced --use-case watchlist
```

Run the opt-in empirical probe, which loads the model and compares representative
series-per-call sizes:

```bash
conda run -n capitalisman-timesfm python -m scripts.timesfm_check \
  --profile thorough --use-case research --autotune
```

The probe recommends a throughput chunk size for that installed GPU, driver,
PyTorch, TimesFM, context, and horizon combination. It does not tune forecast
accuracy. Context length and other analytic choices must still be selected using
chronological out-of-sample evaluation.

To require acceleration when launching the app:

```bash
CAPITALISMAN_TIMESFM_DEVICE=cuda \
  conda run -n capitalisman-timesfm streamlit run app.py
```

## What the Indicator Computes

For the selected analysis horizon, `TimesFM Forecast`:

1. sends only Close prices available at the forecast origin;
2. obtains the point path and nine forecast quantiles;
3. reports median expected return, q10 downside, q90 upside, and interval width;
4. estimates `P(up)` and separate long/short profitability scores from the quantiles; and
5. requires a profitability score of at least 60% and a median move beyond that
   side's fee hurdle before emitting BUY or SELL.

These are uncalibrated model estimates. Interpolation stops at the supplied
q10–q90 boundaries: numeric scores are clipped to 10–90%, and the Predict panel
displays clipped tails as `≤10%` or `≥90%`, rather than claiming certainty.
The benchmark's Brier score uses these clipped numeric estimates.

For a quoted round-trip percentage `c`, each fill charges `f = c / 200` times
its notional. Long break-even is `origin_close * (1+f)/(1-f)`; short break-even is
`origin_close * (1-f)/(1+f)`. Backtests pass their selected cost into forecasting
and execution. These forecast estimates use the known origin close, not the
unknown next opening price, so they are not calibrated probabilities of an
executable trade being profitable.

Backtest preparation explicitly requests historical origins even when the
runtime's profile is interactive. Historical origins follow a fixed grid from
the first eligible context, without adding an extra origin at the data's end;
appending future bars therefore does not change earlier forecast availability.
A forecast from close `t` for `h` bars is
evaluated against the same `t+h` close used for the modeled trade's planned
exit. Failed precomputation is recorded in the frame so historical signal reads
do not retry the entire model at each bar.

Forecast values are written only at actual forecast origins. They are not
forward-filled across bars, which avoids presenting stale forecasts as if they
were newly generated. Signal generation is horizon-aware throughout prediction,
screening, comparison, and backtesting.

## Point-in-Time Benchmark

Use a rolling evaluation before assigning material weight to the model:

```bash
conda run -n capitalisman-timesfm python -m scripts.benchmark_timesfm AAPL \
  --period 5y --horizon 10 --step 10 --device cuda --test-start 2025-01-02 \
  --archive /tmp/aapl-timesfm.zip --output /tmp/aapl-timesfm.json
```

Each origin sees only the history that existed at that origin. The report stores
every origin/target pair and summarizes:

- median return mean absolute error;
- naïve last-price return mean absolute error;
- drift, moving-average and exponential-smoothing baseline errors on identical origins;
- paired block-bootstrap intervals for model-versus-baseline MAE differences;
- directional accuracy;
- q10-q90 empirical coverage and mean width;
- probability-of-up Brier score; and
- q10, q50, and q90 pinball losses.

The archive preserves input bars, configuration, per-origin results and version
metadata. See [Research workflow](RESEARCH_WORKFLOW.md) for fixed baseline
definitions, uncertainty assumptions, bounded suites, held-out strategy comparisons
and replay. Both ZIP and optional JSON destinations must be new. The explicit test date
must be chosen before examining outcomes. Comparisons are descriptive and do
not establish statistical significance or calibrated probabilities.

The model adds forecasting value only if it improves out-of-sample metrics over
simple baselines consistently across symbols, regimes, and horizons. An 80%
interval whose observed coverage is far from 80% is poorly calibrated even when
its point forecast looks accurate.

## Current Limits

- TimesFM is pretrained on general time series, not specifically optimized for
  tradeable risk-adjusted returns.
- Close-only input ignores volume, volatility, fundamentals, and market regime.
- Quantile interpolation is an approximation and clips probability outside the
  provided q10-q90 range.
- Backtests still need realistic slippage, latency, survivorship-bias controls,
  and broader naïve/statistical baselines before supporting investment claims.
- Model downloads require network access on first use; inference can be local
  after weights are cached.

The next development stage should add benchmark result views, multi-asset and
multi-regime evaluation, probability calibration on a held-out window, and a
learned ensemble that can down-weight TimesFM when it fails to beat baselines.
