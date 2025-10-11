# Restormer Remote AI Denoise Server

This FastAPI backend exposes GPU-accelerated endpoints for denoising, detail
refinement, and focus correction with ONNX Runtime (DirectML).  The stack is
optimised for a Windows 11 workstation with an AMD Ryzen 7 5700G APU, 32 GB RAM,
and a Radeon RX 7800 XT discrete GPU.

## Features

- JWT-based authentication with optional Google Sign-In integration.
- Email whitelist enforcement for new accounts plus `/users/verify` for the
  desktop onboarding flow.
- REST endpoints for image upload, job tracking (with progress + stage data),
  and result retrieval.
- Asynchronous pipeline that batches Restormer denoising, motion-deblur, and
  defocus-deblur ONNX models with configurable multi-pass refinement.
- Automatic model caching and DirectML execution provider selection to leverage
  AMD GPUs on Windows, with CPU fallbacks on other platforms.
- Built-in `/dashboard` single-page GUI for live diagnostics, and a
  `/diagnostics/summary` API summarising provider availability and recent jobs.
- SQLite database (via SQLModel) for user and job persistence, including an
  `alloweduser` table that drives the whitelist.

## Environment Setup

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file (optional) to override configuration values. Useful keys
for internet-facing deployments include:

- `RESTORMER_SECRET_KEY` – JWT signing key.
- `RESTORMER_ALLOWED_ORIGINS` – comma-separated list of browser origins (default
  allows all).
- `RESTORMER_PUBLIC_BASE_URL` – the HTTPS address clients should reach (for
  example `https://denoise.example.com`).  When set, job responses include fully
  qualified download URLs.
- `RESTORMER_DASHBOARD_TOKEN` – optional bearer token required by
  `/diagnostics/summary` and the static dashboard UI. Leave blank to allow
  unauthenticated dashboard access.

## Running the Server Locally

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The first request triggers automatic downloads of the required ONNX models into
`server/models_cache`.  Subsequent inferences reuse the cached weights.

The service also initialises (or auto-migrates) database columns for
`progress`, `stage`, and `debug_log` so existing installations gain the richer
telemetry required by the new desktop dashboards.

## Batch Processing & Model Selection

- Each job can include up to 25 source images. The pipeline processes them in
  sequence, applying the chosen Restormer variant for the configured number of
  passes (1x–5x).
- Outputs are written to an archive (`restormer_outputs.zip`) alongside a
  manifest of generated filenames so the client can present per-image status.
- Job progress reflects batch advancement and pass completion, ensuring desktop
  telemetry stays in sync with long-running multi-image submissions.

## Managing the whitelist

Create whitelist entries by inserting rows into the `alloweduser` table. For a
SQLite deployment you can seed the list directly:

```bash
sqlite3 server/restormer.db \
  "INSERT INTO alloweduser (email, display_name, is_active) VALUES ('you@studio.com', 'You', 1);"
```

The desktop client will only allow registrations for emails present in this
table. Successful verification automatically updates `last_verified_at`, giving
administrators visibility into active invitations.

## Operations dashboard

- Visit `https://your-domain/dashboard/` to open the bundled operations GUI.
  It shows provider availability, average job progress, and the most recent
  debug lines without needing to compile a separate frontend.
- The dashboard polls `/diagnostics/summary` every five seconds. Supply
  `X-Dashboard-Token: <RESTORMER_DASHBOARD_TOKEN>` if you configured a token.
- The endpoint returns job counts by status, capped recent jobs (with progress
  and last debug message), and the ONNX providers detected at runtime—ideal for
  remote health monitoring or embedding into your own observability tooling.

## Building a Windows Installer

1. Install PyInstaller and Inno Setup dependencies:
   ```powershell
   pip install pyinstaller==6.3.0
   choco install innosetup -y
   ```
2. Bundle the application:
   ```powershell
   pyinstaller --name RestormerServer --onefile --add-data "app;app" app/main.py
   ```
3. Use the provided `installer/innosetup.iss` script to build a GUI installer
   with Inno Setup (script included under `server/installer`).

## macOS Application Bundle

- Run `installer/macos_installer.sh` (optionally pass a destination directory)
  to generate a `RestormerServer.app` bundle. The script copies the backend
  sources into the bundle, provisions a launch script, and stores shared state
  under `~/Library/Application Support/RestormerServer`.
- On first launch the app bootstraps a Python virtual environment, installs
  `requirements.txt`, pre-downloads all Restormer ONNX models, and then starts
  `uvicorn` bound to `0.0.0.0:8000`.
- Subsequent launches reuse the cached environment and simply restart the
  service while tailing logs to `~/Library/Application Support/RestormerServer/logs/restormer-server.log`.

## Production Notes

- Configure a reverse proxy (e.g. Nginx or Caddy) with HTTPS termination.
- Expose the FastAPI service on port 8000 (or your chosen port) and ensure the
  firewall forwards TCP traffic from the public internet to the host.
- Set `RESTORMER_PUBLIC_BASE_URL` to the externally accessible hostname so the
  API can generate absolute download links for the desktop client.
- Set environment variables `RESTORMER_SECRET_KEY`, `GOOGLE_CLIENT_ID`, and
  `GOOGLE_CLIENT_SECRET` in production.
- For persistent storage, use an external database (PostgreSQL) by updating the
  `database_url` value in `.env`.
