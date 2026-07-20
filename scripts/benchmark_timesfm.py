"""Run a rolling, point-in-time TimesFM benchmark for a market symbol."""

import argparse
import json
from pathlib import Path

from data.fetcher import fetch_ohlcv
from ml.benchmark import benchmark_close_series
from ml.timesfm_runtime import TimesFMRuntime, TimesFMRuntimeConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="Yahoo Finance symbol, for example AAPL")
    parser.add_argument("--period", default="2y")
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--step", type=int)
    parser.add_argument("--min-context", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    prices = fetch_ohlcv(args.ticker, period=args.period)["Close"]
    runtime = TimesFMRuntime(TimesFMRuntimeConfig(device=args.device))
    result = benchmark_close_series(
        prices,
        runtime,
        horizon=args.horizon,
        min_context=args.min_context,
        step=args.step,
        batch_size=args.batch_size,
    )
    payload = json.dumps(result.to_dict(), indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
