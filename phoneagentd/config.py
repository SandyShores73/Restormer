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
        )
