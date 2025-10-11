# Restormer Remote Suite

This repository contains a GPU-enabled remote denoise/detail refinement platform
consisting of a FastAPI backend and an Electron-based desktop client for macOS
and Windows.

[Server Setup Guide](server/README.md) · [Client Setup Guide](client/README.md)

## Structure

- `server/` – FastAPI application with DirectML-accelerated ONNX inference,
  SQLite persistence, JWT authentication, whitelist enforcement, live job
  progress, and an embedded diagnostics dashboard.
- `client/` – Electron + React desktop client packaged as `.dmg` (macOS) and
  `.exe` (Windows) via electron-builder.

## Quick Start

1. Follow `server/README.md` to configure the backend.
2. Follow `client/README.md` to run/build the desktop client.

## Deployment Notes

- Host the backend on a Windows 11 workstation with the AMD RX 7800 XT to take
  advantage of DirectML GPU acceleration.
- Use HTTPS and secure password hashing in production environments.
- Seed the `alloweduser` table so that new accounts can be approved during the
  desktop onboarding flow; see `server/README.md` for quick SQL helpers.
- Monitor `/dashboard` for a glassmorphism control centre that surfaces ONNX
  providers, job counts, progress, and the latest debug lines.
- When exposing the service on the public internet, configure
  `RESTORMER_PUBLIC_BASE_URL` and `RESTORMER_ALLOWED_ORIGINS` so the desktop
  client can discover download links while keeping CORS tight to your domain.
- For Codex-based distribution workflows, see `docs/publish_via_codex.md` for
  instructions on preparing installers and publishing releases.
