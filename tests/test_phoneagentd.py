from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

from phoneagentd.config import Config
from phoneagentd.model import parse_action_dsl
from phoneagentd.orchestrator import AgentOrchestrator
from phoneagentd.safety import requires_approval
from phoneagentd.server import GatewayState, make_handler


class MockRpc:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((method, params or {}))
        return {"result": {"ok": True, "method": method}, "elapsed_ms": 1.0}


def make_server() -> tuple[str, GatewayState, ThreadingHTTPServer]:
    cfg = Config(port=0, token="test-token", require_tailscale=False)
    state = GatewayState(cfg, rpc=MockRpc())  # type: ignore[arg-type]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{httpd.server_address[1]}", state, httpd


def request(base: str, path: str, *, token: str | None = "test-token", method: str = "GET", body: dict[str, Any] | None = None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, headers=headers, method=method, data=data)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode())


class PhoneAgentDTests(unittest.TestCase):
    def test_gateway_rejects_missing_and_wrong_auth(self) -> None:
        base, _state, httpd = make_server()
        try:
            for token in (None, "wrong"):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    request(base, "/health", token=token)
                self.assertEqual(ctx.exception.code, 401)
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_gateway_accepts_correct_auth_and_health_works(self) -> None:
        base, _state, httpd = make_server()
        try:
            status, payload = request(base, "/health")
            self.assertEqual(status, 200)
            self.assertEqual(payload["status"], "ok")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_command_schema_validation(self) -> None:
        base, _state, httpd = make_server()
        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                request(base, "/v1/commands", method="POST", body={"action": "format_disk", "params": {}, "risk": "low"})
            self.assertEqual(ctx.exception.code, 400)
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_risky_action_pending_and_approval_forwards_to_rpc(self) -> None:
        base, state, httpd = make_server()
        try:
            status, pending = request(
                base,
                "/v1/commands",
                method="POST",
                body={"action": "tap_element", "params": {"label": "Send"}, "reason": "send message", "risk": "high"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(pending["status"], "needs_approval")
            session_id = pending["session_id"]
            status, approved = request(
                base,
                f"/v1/sessions/{session_id}/approve",
                method="POST",
                body={"command_id": pending["command_id"], "approved": True},
            )
            self.assertEqual(status, 200)
            self.assertEqual(approved["status"], "executed")
            self.assertEqual(state.rpc.calls[-1], ("tap_element", {"label": "Send"}))  # type: ignore[attr-defined]
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_status_exposes_latency_and_voice_options(self) -> None:
        base, _state, httpd = make_server()
        try:
            status, payload = request(base, "/v1/status")
            self.assertEqual(status, 200)
            self.assertIn("latency_options", payload)
            self.assertIn("latency_descriptions", payload)
            self.assertTrue(payload["voice_break_mode"])
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_voice_interjection_lifecycle(self) -> None:
        base, _state, httpd = make_server()
        try:
            status, created = request(
                base,
                "/v1/interjections",
                method="POST",
                body={"question": "Can I send this?", "silence_ms": 700, "transcript_mode": "controller_only"},
            )
            self.assertEqual(status, 201)
            self.assertEqual(created["status"], "listening_for_break")
            self.assertIn("battery_policy", created)
            status, completed = request(
                base,
                f"/v1/interjections/{created['id']}/complete",
                method="POST",
                body={"delivered": True},
            )
            self.assertEqual(status, 200)
            self.assertEqual(completed["status"], "delivered")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_local_model_dsl_parser_accepts_valid_json(self) -> None:
        parsed = parse_action_dsl(
            json.dumps(
                {
                    "status": "action",
                    "action": {"type": "open_app", "params": {"name": "Settings"}},
                    "confidence": 0.9,
                    "reason": "Open Settings.",
                    "memory_update": "",
                    "requires_approval": False,
                }
            )
        )
        self.assertEqual(parsed["action"]["type"], "open_app")

    def test_parser_rejects_malformed_and_unsafe_actions(self) -> None:
        for text in ("not json", json.dumps({"status": "action", "action": {"type": "stop", "params": {}}, "confidence": 0.9})):
            with self.assertRaises(ValueError):
                parse_action_dsl(text)

    def test_safety_reviewer_blocks_sensitive_actions(self) -> None:
        self.assertTrue(requires_approval("tap_element", {"label": "Delete"}, "delete this message", "low"))
        self.assertTrue(requires_approval("enter_text", {"text": "send bank transfer"}, "payment", "low"))
        self.assertFalse(requires_approval("open_app", {"name": "Photos"}, "navigation", "low"))

    def test_session_state_compact_and_no_raw_screenshot_storage_by_default(self) -> None:
        orch = AgentOrchestrator("summarize the screen")
        for i in range(20):
            orch.state.remember_action("get_tree", f"summary {i}")
        view = orch.compact_view()
        self.assertEqual(len(view["last_actions"]), 12)
        self.assertFalse(view["raw_screenshots_stored"])


if __name__ == "__main__":
    unittest.main()
