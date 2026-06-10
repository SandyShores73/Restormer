from __future__ import annotations

import argparse
import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address, ip_network
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from .config import Config
from .orchestrator import AgentOrchestrator
from .rpc import RpcClient
from .safety import redact, requires_approval, summarize_result, validate_action

TAILNET_NETWORKS = [ip_network("100.64.0.0/10"), ip_network("fd7a:115c:a1e0::/48")]
LOCAL_NETWORKS = [ip_network("127.0.0.0/8"), ip_network("::1/128")]


@dataclass
class CommandRecord:
    session_id: str
    action: str
    params: dict[str, Any]
    reason: str
    risk: str
    approval_state: str
    timestamp: float = field(default_factory=time.time)
    result_summary: str = ""
    command_id: str = field(default_factory=lambda: str(uuid4()))


class GatewayState:
    def __init__(self, config: Config, rpc: RpcClient | None = None) -> None:
        self.config = config
        self.rpc = rpc or RpcClient(config.rpc_host, config.rpc_port)
        self.sessions: dict[str, dict[str, Any]] = {}
        self.pending: dict[str, CommandRecord] = {}
        self.events: list[dict[str, Any]] = []
        self.lock = threading.RLock()
        self.started_at = time.time()

    def emit(self, event: str, data: dict[str, Any]) -> None:
        item = {"id": str(uuid4()), "time": time.time(), "event": event, "data": redact(data)}
        with self.lock:
            self.events.append(item)
            self.events = self.events[-200:]

    def create_session(self, goal: str = "") -> dict[str, Any]:
        orch = AgentOrchestrator(goal, store_raw_screenshots=self.config.store_raw_screenshots)
        session = {"id": orch.state.session_id, "status": "ready", "goal": goal, "compact_state": orch.compact_view()}
        with self.lock:
            self.sessions[session["id"]] = session
        self.emit("session.created", session)
        return session

    def execute_command(self, command: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
        action = command.get("action")
        params = command.get("params") or {}
        reason = command.get("reason", "")
        risk = command.get("risk", "low")
        explicit = bool(command.get("requires_approval", False))
        if not isinstance(action, str) or not isinstance(params, dict):
            raise ValueError("command requires string action and object params")
        if risk not in {"low", "medium", "high"}:
            raise ValueError("risk must be low, medium, or high")
        validate_action(action)
        session_id = command.get("session_id") or self.create_session(reason).get("id")
        must_approve = explicit or requires_approval(action, params, reason, risk)
        record = CommandRecord(session_id, action, params, reason, risk, "approved" if force else "direct")
        if must_approve and not force:
            record.approval_state = "pending"
            with self.lock:
                self.pending[record.command_id] = record
            self.emit("command.pending_approval", asdict(record))
            return {"status": "needs_approval", "command_id": record.command_id, "session_id": session_id}
        rpc_result = self.rpc.call(action, params)
        record.result_summary = summarize_result(rpc_result.get("result"))
        self.emit("command.executed", asdict(record))
        return {"status": "executed", "command_id": record.command_id, "session_id": session_id, **rpc_result}

    def approve(self, command_id: str, approved: bool) -> dict[str, Any]:
        with self.lock:
            record = self.pending.pop(command_id, None)
        if not record:
            raise KeyError("pending command not found")
        if not approved:
            record.approval_state = "denied"
            self.emit("command.denied", asdict(record))
            return {"status": "denied", "command_id": command_id}
        return self.execute_command(asdict(record), force=True)


def _authorized(handler: BaseHTTPRequestHandler, state: GatewayState) -> bool:
    token = state.config.token
    if not token:
        _send(handler, HTTPStatus.SERVICE_UNAVAILABLE, {"error": "PHONEAGENTD_TOKEN is required"})
        return False
    expected = f"Bearer {token}"
    if not secrets.compare_digest(handler.headers.get("Authorization", ""), expected):
        _send(handler, HTTPStatus.UNAUTHORIZED, {"error": "missing or invalid bearer token"})
        return False
    if state.config.require_tailscale and not _is_allowed_remote(handler.client_address[0]):
        _send(handler, HTTPStatus.FORBIDDEN, {"error": "request is not from localhost or a Tailscale address"})
        return False
    return True


def _is_allowed_remote(host: str) -> bool:
    try:
        remote = ip_address(host)
    except ValueError:
        return False
    return any(remote in net for net in LOCAL_NETWORKS + TAILNET_NETWORKS)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def _send(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(state: GatewayState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "phoneagentd/0.1"

        def do_GET(self) -> None:  # noqa: N802
            if not _authorized(self, state):
                return
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                if path == "/health":
                    _send(self, HTTPStatus.OK, {"status": "ok", "uptime_s": round(time.time() - state.started_at, 2)})
                elif path == "/v1/status":
                    _send(self, HTTPStatus.OK, {"status": "ready", "bridge": f"{state.config.rpc_host}:{state.config.rpc_port}"})
                elif path.startswith("/v1/sessions/"):
                    session_id = path.rsplit("/", 1)[-1]
                    session = state.sessions.get(session_id)
                    _send(self, HTTPStatus.OK if session else HTTPStatus.NOT_FOUND, session or {"error": "session not found"})
                elif path == "/v1/events":
                    _send(self, HTTPStatus.OK, {"events": state.events[-50:]})
                else:
                    _send(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            except Exception as exc:  # defensive API boundary
                _send(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            if not _authorized(self, state):
                return
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                body = _read_json(self)
                if path == "/v1/sessions":
                    _send(self, HTTPStatus.CREATED, state.create_session(str(body.get("goal", ""))))
                elif path == "/v1/commands":
                    _send(self, HTTPStatus.OK, state.execute_command(body))
                elif path.startswith("/v1/sessions/") and path.endswith("/cancel"):
                    session_id = path.split("/")[3]
                    result = state.rpc.call("stop", {})
                    state.emit("session.cancelled", {"session_id": session_id, "result": summarize_result(result)})
                    _send(self, HTTPStatus.OK, {"status": "cancelled", "session_id": session_id})
                elif path.startswith("/v1/sessions/") and path.endswith("/approve"):
                    approved = bool(body.get("approved", True))
                    command_id = str(body.get("command_id", ""))
                    _send(self, HTTPStatus.OK, state.approve(command_id, approved))
                else:
                    _send(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            except json.JSONDecodeError:
                _send(self, HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            except (ValueError, KeyError) as exc:
                _send(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except Exception as exc:  # defensive API boundary
                _send(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

        def log_message(self, fmt: str, *args: Any) -> None:
            # Avoid logging raw request bodies or Authorization headers.
            print(f"{self.address_string()} - {fmt % args}")

    return Handler


def run(config: Config | None = None) -> None:
    config = config or Config.from_env()
    state = GatewayState(config)
    httpd = ThreadingHTTPServer((config.bind_host, config.port), make_handler(state))
    print(f"phoneagentd listening on http://{config.bind_host}:{config.port}")
    httpd.serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Secure tailnet gateway for PhoneAgent")
    parser.add_argument("--check-token", action="store_true", help="exit non-zero if PHONEAGENTD_TOKEN is missing")
    args = parser.parse_args(argv)
    config = Config.from_env()
    if args.check_token:
        raise SystemExit(0 if config.token else 2)
    run(config)


if __name__ == "__main__":
    main()
