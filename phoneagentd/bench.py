from __future__ import annotations

import argparse
import statistics
import time

from .config import Config
from .rpc import RpcClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure average PhoneAgent JSON-RPC latency")
    parser.add_argument("--action", default="get_tree")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    cfg = Config.from_env()
    client = RpcClient(cfg.rpc_host, cfg.rpc_port)
    timings = []
    for _ in range(args.count):
        started = time.perf_counter()
        client.call(args.action, {})
        timings.append((time.perf_counter() - started) * 1000)
    print(f"{args.action}: avg={statistics.mean(timings):.2f}ms min={min(timings):.2f}ms max={max(timings):.2f}ms")


if __name__ == "__main__":
    main()
