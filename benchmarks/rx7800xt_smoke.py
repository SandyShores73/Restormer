#!/usr/bin/env python3
"""Focused smoke benchmark scaffold for RX 7800 XT validation.

This command intentionally avoids importing heavyweight inference modules at
import time. It records environment details and emits the exact mode/image size
that should be used when wiring in the ONNX/DirectML pipeline on the target host.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SmokeResult:
    mode: str
    image_size: int
    warmup_runs: int
    measured_runs: int
    elapsed_seconds: float
    python: str
    platform: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RX 7800 XT smoke benchmark scaffold")
    parser.add_argument(
        "--mode",
        choices=("cpu", "directml"),
        default="cpu",
        help="Execution provider path to validate; use directml on the RX 7800 XT host.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=512,
        help="Square synthetic input size used by the eventual model benchmark.",
    )
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--measured-runs", type=int, default=3)
    return parser.parse_args()


def run_smoke(args: argparse.Namespace) -> SmokeResult:
    start = time.perf_counter()
    # Lightweight placeholder loop keeps CI fast while preserving the benchmark CLI.
    for _ in range(args.warmup_runs + args.measured_runs):
        _ = args.image_size * args.image_size
    elapsed = time.perf_counter() - start
    return SmokeResult(
        mode=args.mode,
        image_size=args.image_size,
        warmup_runs=args.warmup_runs,
        measured_runs=args.measured_runs,
        elapsed_seconds=round(elapsed, 6),
        python=platform.python_version(),
        platform=platform.platform(),
    )


def main() -> None:
    result = run_smoke(parse_args())
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
