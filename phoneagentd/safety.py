from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = re.compile(r"(api[_-]?key|token|secret|password|passcode|otp|2fa|private[_-]?key)", re.I)
SENSITIVE_TEXT = re.compile(
    r"(\b\d{4,8}\b|sk-[A-Za-z0-9_-]{12,}|[A-Za-z0-9+/]{32,}={0,2}|password\s*[:=])",
    re.I,
)
RISKY_WORDS = re.compile(
    r"\b(send|sent|email|message|delete|remove|purchase|buy|pay|transfer|bank|apple id|"
    r"passcode|password|2fa|two[- ]factor|security|contact|calendar|private key|secret|otp)\b",
    re.I,
)
RISKY_ACTIONS = {"enter_text", "tap", "tap_element", "swipe"}
ALLOWED_ACTIONS = {
    "open_app",
    "tap",
    "tap_element",
    "enter_text",
    "scroll",
    "swipe",
    "get_tree",
    "get_screen_image",
    "get_context",
    "stop",
    "wait",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            out[key] = "[REDACTED]" if SENSITIVE_KEYS.search(str(key)) else redact(item)
        return out
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        if len(value) > 256:
            value = value[:256] + "…"
        return SENSITIVE_TEXT.sub("[REDACTED]", value)
    return value


def summarize_result(result: Any) -> str:
    safe = redact(result)
    text = str(safe)
    return text if len(text) <= 240 else text[:237] + "..."


def requires_approval(action: str, params: dict[str, Any] | None, reason: str = "", risk: str = "low") -> bool:
    params = params or {}
    joined = " ".join([action, reason, str(redact(params))])
    if risk in {"medium", "high"}:
        return True
    if action in RISKY_ACTIONS and RISKY_WORDS.search(joined):
        return True
    return False


def validate_action(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action: {action}")
