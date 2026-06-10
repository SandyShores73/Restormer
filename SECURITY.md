# PhoneAgent Tailnet Gateway Security

## Security model

`phoneagentd` is a thin authenticated gateway in front of the existing
PhoneAgent JSON-RPC bridge. The raw bridge remains bound to `127.0.0.1:45678` by
default and should not be exposed directly.

The gateway is designed for tailnet-only access from trusted devices, for
example an M3 Pro MacBook Pro host controlled by an iPhone 14 Pro over
Tailscale. It is not designed for public internet exposure.

## Hard requirements

- Set `PHONEAGENTD_TOKEN`; requests without `Authorization: Bearer <token>` are
  rejected.
- Keep `PHONEAGENTD_BIND_HOST=127.0.0.1` unless you deliberately bind to a
  tailnet interface.
- Use Tailscale Serve for tailnet sharing. Do **not** use Tailscale Funnel.
- Restrict Tailscale ACLs to only your controller devices.
- Keep `PHONEAGENTD_REQUIRE_TAILSCALE=true` when accepting remote requests.
- Do not expose the raw JSON-RPC bridge to the internet.

## Approval policy

The gateway forces pending approval for medium/high risk commands and for actions
that look like sending, deleting, purchasing, payments, banking transfers,
account/security changes, contacts/calendar/messages mutation, 2FA/passcode
handling, private-key/secret handling, or similar sensitive operations.

## Logging and privacy

Command logs and events redact values that look like passwords, tokens, API keys,
OTPs, passcodes, and long secrets. Raw screenshots are not stored by default and
should not be sent to cloud models unless the user explicitly enables that.


## Voice interjection safety

Natural-break microphone mode must be short-lived. The controller should open the
mic only while an interjection is pending, use on-device or local speech activity
detection where possible, and close the mic immediately after delivery, cancel,
or timeout. Do not send audio or transcripts to cloud services unless the user
explicitly enables that mode.

## Low-latency safety

Ultra-low-latency mode can prefetch screenshot thumbnails and optimistically run
low-risk navigation. Keep raw screenshots local by default, continue requiring
approval for risky actions, and make the battery/privacy trade-off visible in the
controller UI.
