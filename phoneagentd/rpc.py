from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class RpcClient:
    host: str = "127.0.0.1"
    port: int = 45678
    timeout: float = 15.0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": method, "params": params or {}}
        started = time.perf_counter()
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            sock.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
            response = self._readline(sock)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        payload = json.loads(response)
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return {"result": payload.get("result"), "elapsed_ms": elapsed_ms}

    @staticmethod
    def _readline(sock: socket.socket) -> str:
        data = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                break
            if chunk == b"\n":
                break
            data.extend(chunk)
        if not data:
            raise RuntimeError("empty JSON-RPC response")
        return data.decode("utf-8")
