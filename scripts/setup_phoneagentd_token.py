#!/usr/bin/env python3
from __future__ import annotations

import secrets
from pathlib import Path

TOKEN = secrets.token_urlsafe(32)
path = Path(".env.local")
if path.exists():
    print(".env.local already exists; not overwriting.")
    print(f"Add or rotate manually: PHONEAGENTD_TOKEN={TOKEN}")
else:
    path.write_text(
        "PHONEAGENTD_BIND_HOST=127.0.0.1\n"
        "PHONEAGENTD_PORT=8788\n"
        "PHONEAGENT_RPC_HOST=127.0.0.1\n"
        "PHONEAGENT_RPC_PORT=45678\n"
        f"PHONEAGENTD_TOKEN={TOKEN}\n"
        "PHONEAGENTD_REQUIRE_TAILSCALE=true\n"
        "PHONEAGENT_MODEL_BASE_URL=http://127.0.0.1:1234/v1\n"
        "PHONEAGENT_MODEL_NAME=gemma-4-12b\n"
        "PHONEAGENT_MODEL_API_KEY=not-needed-or-local-key\n"
        "PHONEAGENT_LOW_CONTEXT_MODE=true\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    print("Wrote .env.local with a generated PHONEAGENTD_TOKEN. Do not commit it.")
