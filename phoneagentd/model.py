from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from .safety import ALLOWED_ACTIONS, requires_approval

DSL_ACTIONS = ALLOWED_ACTIONS - {"get_context", "stop"}
DSL_STATUSES = {"action", "ask_user", "needs_approval", "done", "failed"}


@dataclass
class ModelProvider:
    base_url: str
    model: str
    api_key: str | None = None
    max_output_tokens: int = 512
    timeout: float = 60.0

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.1) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_output_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]


def parse_action_dsl(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("model output is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("model output must be a JSON object")
    status = data.get("status")
    if status not in DSL_STATUSES:
        raise ValueError("invalid DSL status")
    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise ValueError("confidence must be between 0 and 1")
    action = data.get("action")
    if status in {"action", "needs_approval"}:
        if not isinstance(action, dict):
            raise ValueError("action status requires an action object")
        action_type = action.get("type")
        if action_type not in DSL_ACTIONS:
            raise ValueError("unsafe or unsupported DSL action")
        params = action.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("action params must be an object")
        if action_type in {"tap", "tap_element"} and confidence < 0.35:
            raise ValueError("low-confidence coordinate/element action rejected")
    elif action not in (None, {}):
        raise ValueError("non-action status must not include executable action")
    computed_approval = False
    if isinstance(action, dict):
        computed_approval = requires_approval(
            str(action.get("type", "")),
            action.get("params", {}),
            str(data.get("reason", "")),
            "high" if status == "needs_approval" else "low",
        )
    data["requires_approval"] = bool(data.get("requires_approval") or computed_approval)
    return data
