#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socketserver
import time
from typing import Any


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        for line in self.rfile:
            try:
                request = json.loads(line.decode("utf-8"))
                method = request.get("method")
                params = request.get("params") or {}
                result: dict[str, Any] = {
                    "ok": True,
                    "method": method,
                    "params": params,
                    "mocked_at": time.time(),
                }
                if method == "get_tree":
                    result["tree"] = {"role": "root", "children": [{"label": "Mock Button", "role": "button"}]}
                payload = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
            except Exception as exc:
                payload = {"jsonrpc": "2.0", "id": None, "error": str(exc)}
            self.wfile.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock PhoneAgent newline-delimited JSON-RPC bridge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=45678)
    args = parser.parse_args()
    with socketserver.ThreadingTCPServer((args.host, args.port), Handler) as server:
        print(f"mock PhoneAgent RPC listening on {args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
