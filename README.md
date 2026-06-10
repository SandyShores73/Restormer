# PhoneAgent Tailnet Gateway Layer

> Note: this checkout does not include the original PhoneAgent SwiftUI/XCTest or
> Android bridge sources. The changes here add the requested thin, secure,
> local-first gateway and orchestration layer without replacing the existing
> PhoneAgent bridge.

## What changed

- Added `phoneagentd`, a small Python gateway that talks to the existing
  newline-delimited JSON-RPC PhoneAgent bridge on `127.0.0.1:45678`.
- Kept the raw RPC bridge localhost-oriented; remote access is intended through
  Tailscale Serve or an explicit tailnet bind only.
- Added bearer-token authentication, tailnet/localhost request checks, command
  approval handling, redacted logs/events, and mockable tests.
- Added a compact local-model orchestration layer for weaker OpenAI-compatible
  local models such as LM Studio, Ollama, llama.cpp server, and vLLM.
- Added iOS controller and Dynamic Island implementation notes for the actual
  PhoneAgent Xcode project.

## Architecture

```text
[iPhone Controller]
    |  HTTPS/Tailscale Serve + Bearer token
    v
[M3 Pro Mac: phoneagentd on 127.0.0.1:8788]
    |  newline-delimited JSON-RPC, localhost only
    v
[Existing PhoneAgent bridge on 127.0.0.1:45678]
    |  XCTest / Android bridge actions
    v
[iPhone simulator, physical iPhone, or Android device]

Optional local model:
[phoneagentd orchestration] -> [LM Studio/Ollama/llama.cpp/vLLM OpenAI-compatible /v1]
```

## Gateway API

All endpoints require `Authorization: Bearer <PHONEAGENTD_TOKEN>`.

- `GET /health`
- `GET /v1/status`
- `POST /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `POST /v1/sessions/{session_id}/cancel`
- `POST /v1/sessions/{session_id}/approve`
- `POST /v1/commands`
- `GET /v1/events`

Command body:

```json
{
  "action": "open_app | tap | tap_element | enter_text | scroll | swipe | get_tree | get_screen_image | get_context | stop",
  "params": {},
  "reason": "short reason",
  "risk": "low | medium | high",
  "requires_approval": true
}
```

Low-risk navigation can execute directly. Medium/high-risk commands, explicit
`requires_approval`, and send/delete/purchase/payment/account/security/contact/
calendar/message-like actions create a pending approval. The approval endpoint
executes the pending command only after approval.

## Configuration

Copy `examples/phoneagentd.env.example` or run the setup script.

```bash
python3 scripts/setup_phoneagentd_token.py
set -a; source .env.local; set +a
```

Example environment:

```dotenv
PHONEAGENTD_BIND_HOST=127.0.0.1
PHONEAGENTD_PORT=8788
PHONEAGENT_RPC_HOST=127.0.0.1
PHONEAGENT_RPC_PORT=45678
PHONEAGENTD_TOKEN=replace-with-generated-token
PHONEAGENTD_REQUIRE_TAILSCALE=false
PHONEAGENT_MODEL_BASE_URL=http://127.0.0.1:1234/v1
PHONEAGENT_MODEL_NAME=gemma-4-12b
PHONEAGENT_MODEL_API_KEY=not-needed-or-local-key
PHONEAGENT_LOW_CONTEXT_MODE=true
```

## Running the gateway

```bash
python3 -m phoneagentd
curl -H "Authorization: Bearer $PHONEAGENTD_TOKEN" http://127.0.0.1:8788/health
```

Benchmark raw bridge latency with:

```bash
python3 -m phoneagentd.bench --action get_tree --count 5
```

For local testing without a device bridge, run the mock RPC server in another
terminal:

```bash
python3 scripts/mock_phoneagent_rpc.py --host 127.0.0.1 --port 45678
```

## Tailscale setup

Keep the gateway bound to localhost and share it only inside your tailnet:

```bash
# Start PhoneAgent gateway locally
python3 -m phoneagentd
# Share only inside the tailnet, not publicly
tailscale serve 8788
# Verify status
tailscale serve status
```

Use Tailscale ACLs to restrict access to only your iPhone/controller devices.
Do **not** use Tailscale Funnel. Funnel exposes services to the public internet,
which is not appropriate for a mobile automation control plane.

## Local model setup

`ModelProvider` targets OpenAI-compatible `/v1/chat/completions` servers. Use a
local endpoint where possible:

- LM Studio: `PHONEAGENT_MODEL_BASE_URL=http://127.0.0.1:1234/v1`
- Ollama OpenAI-compatible endpoint: `http://127.0.0.1:11434/v1`
- llama.cpp server or vLLM: set the local `/v1` base URL and model name.

Low-context mode is on by default. The orchestrator keeps compact state, prefers
`get_tree`, avoids screenshots unless needed, performs one UI action at a time,
and re-observes after meaningful actions.

## iOS and Dynamic Island setup

See `docs/ios_controller.md`. In the actual PhoneAgent Xcode project, add:

- Gateway URL and Keychain token settings.
- Cloud/OpenAI, local OpenAI-compatible, and manual gateway-only modes.
- A black Siri-style controller UI with visible Pause/Stop.
- Approval cards for pending risky actions.
- ActivityKit Widget Extension for a Live Activity that appears while armed or
  running, with `phoneagent://request`, `phoneagent://session/{id}`, and
  `phoneagent://approve/{id}` deep links.

A Live Activity cannot permanently live in the Dynamic Island; start it when the
user arms/starts a session and end it when idle or stopped.

## Safety model

- Raw RPC remains localhost-only.
- Gateway authentication is required even inside Tailscale.
- Logs/events redact secrets, tokens, passwords, passcodes, OTPs, and API keys.
- Raw screenshots are not stored by default.
- Risky actions enter `needs_approval`.
- Never automate passcodes, Apple ID changes, payment confirmations, purchases,
  banking transfers, deleting data, security settings, 2FA approval,
  private-key/secret handling, or sending messages/emails without explicit user
  approval.

## Troubleshooting

- `401`: missing or wrong bearer token.
- `403`: `PHONEAGENTD_REQUIRE_TAILSCALE=true` rejected a non-local/non-tailnet
  source.
- `503`: `PHONEAGENTD_TOKEN` is not set.
- `500` on commands: confirm the existing PhoneAgent bridge is running at
  `PHONEAGENT_RPC_HOST:PHONEAGENT_RPC_PORT`.
- Model failures: verify your local OpenAI-compatible server, model name, and
  `/v1/chat/completions` support.
