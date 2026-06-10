from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bind_host: str = "127.0.0.1"
    port: int = 8788
    rpc_host: str = "127.0.0.1"
    rpc_port: int = 45678
    token: str | None = None
    require_tailscale: bool = True
    model_base_url: str = "http://127.0.0.1:1234/v1"
    model_name: str = "gemma-4-12b"
    model_api_key: str | None = None
    model_max_context: int = 8192
    model_max_output_tokens: int = 512
    low_context_mode: bool = True
    store_raw_screenshots: bool = False
    latency_profile: str = "balanced"
    voice_break_mode: bool = True
    voice_break_max_listen_seconds: int = 45
    voice_break_silence_ms: int = 900

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bind_host=os.getenv("PHONEAGENTD_BIND_HOST", "127.0.0.1"),
            port=int(os.getenv("PHONEAGENTD_PORT", "8788")),
            rpc_host=os.getenv("PHONEAGENT_RPC_HOST", "127.0.0.1"),
            rpc_port=int(os.getenv("PHONEAGENT_RPC_PORT", "45678")),
            token=os.getenv("PHONEAGENTD_TOKEN"),
            require_tailscale=os.getenv("PHONEAGENTD_REQUIRE_TAILSCALE", "true").lower()
            in {"1", "true", "yes", "on"},
            model_base_url=os.getenv("PHONEAGENT_MODEL_BASE_URL", "http://127.0.0.1:1234/v1"),
            model_name=os.getenv("PHONEAGENT_MODEL_NAME", "gemma-4-12b"),
            model_api_key=os.getenv("PHONEAGENT_MODEL_API_KEY") or None,
            model_max_context=int(os.getenv("PHONEAGENT_MODEL_MAX_CONTEXT", "8192")),
            model_max_output_tokens=int(os.getenv("PHONEAGENT_MODEL_MAX_OUTPUT_TOKENS", "512")),
            low_context_mode=os.getenv("PHONEAGENT_LOW_CONTEXT_MODE", "true").lower()
            in {"1", "true", "yes", "on"},
            store_raw_screenshots=os.getenv("PHONEAGENT_STORE_RAW_SCREENSHOTS", "false").lower()
            in {"1", "true", "yes", "on"},
            latency_profile=os.getenv("PHONEAGENT_LATENCY_PROFILE", "balanced"),
            voice_break_mode=os.getenv("PHONEAGENT_VOICE_BREAK_MODE", "true").lower()
            in {"1", "true", "yes", "on"},
            voice_break_max_listen_seconds=int(os.getenv("PHONEAGENT_VOICE_BREAK_MAX_LISTEN_SECONDS", "45")),
            voice_break_silence_ms=int(os.getenv("PHONEAGENT_VOICE_BREAK_SILENCE_MS", "900")),
        )
