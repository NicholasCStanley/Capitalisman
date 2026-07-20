"""Inspect the TimesFM runtime and optionally perform a model smoke test."""

import argparse
from dataclasses import asdict
import json

import numpy as np

from ml.timesfm_runtime import TimesFMRuntime, TimesFMRuntimeConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--smoke", action="store_true", help="Load weights and forecast")
    args = parser.parse_args()

    runtime = TimesFMRuntime(TimesFMRuntimeConfig(device=args.device))
    status = runtime.preflight()
    print(json.dumps(asdict(status), indent=2))
    if status.state != "ready":
        return 1
    if args.smoke:
        forecast = runtime.forecast(
            [np.linspace(100.0, 110.0, 128, dtype=np.float32)], horizon=5
        )[0]
        print(
            json.dumps(
                {
                    "point": forecast.point.tolist(),
                    "q10": forecast.quantiles[0.1].tolist(),
                    "q50": forecast.quantiles[0.5].tolist(),
                    "q90": forecast.quantiles[0.9].tolist(),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
