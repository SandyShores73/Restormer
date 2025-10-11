<<<<<<< HEAD
# Restormer Remote AI Denoise Server

This FastAPI backend exposes GPU-accelerated endpoints for denoising, detail
refinement, and focus correction with ONNX Runtime (DirectML).  The stack is
optimised for a Windows 11 workstation with an AMD Ryzen 7 5700G APU, 32 GB RAM,
and a Radeon RX 7800 XT discrete GPU.

## Features

- JWT-based authentication with optional Google Sign-In integration.
- REST endpoints for image upload, job tracking, and result retrieval.
- Asynchronous pipeline that chains Restormer (denoise), Real-ESRGAN (detail
  enhancement), and NAFNet Deblur (focus correction) models.
- Automatic model caching and DirectML execution provider selection to leverage
  AMD GPUs on Windows, with CPU fallbacks on other platforms.
- SQLite database (via SQLModel) for user and job persistence.

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

## Running the Server Locally

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The first request triggers automatic downloads of the required ONNX models into
`server/models_cache`.  Subsequent inferences reuse the cached weights.

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
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/server/README.md
index 0000000000000000000000000000000000000000..b7d539a1c03aa17d2a1320cddfc47b199b015f25 100644
--- a//dev/null
+++ b/server/README.md
@@ -0,0 +1,58 @@
+# Restormer Remote AI Denoise Server
+
+This FastAPI backend exposes GPU-accelerated endpoints for denoising, detail
+refinement, and focus correction with ONNX Runtime (DirectML).  The stack is
+optimised for a Windows 11 workstation with an AMD Ryzen 7 5700G APU, 32 GB RAM,
+and a Radeon RX 7800 XT discrete GPU.
+
+## Features
+
+- JWT-based authentication with optional Google Sign-In integration.
+- REST endpoints for image upload, job tracking, and result retrieval.
+- Asynchronous pipeline that chains Restormer (denoise), Real-ESRGAN (detail
+  enhancement), and NAFNet Deblur (focus correction) models.
+- Automatic model caching and DirectML execution provider selection to leverage
+  AMD GPUs on Windows.
+- SQLite database (via SQLModel) for user and job persistence.
+
+## Environment Setup
+
+```powershell
+python -m venv .venv
+.venv\\Scripts\\Activate.ps1
+pip install -r requirements.txt
+```
+
+Create a `.env` file (optional) to override configuration values such as the
+JWT secret key or allowed CORS origins.
+
+## Running the Server Locally
+
+```powershell
+uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
+```
+
+The first request triggers automatic downloads of the required ONNX models into
+`server/models_cache`.  Subsequent inferences reuse the cached weights.
+
+## Building a Windows Installer
+
+1. Install PyInstaller and Inno Setup dependencies:
+   ```powershell
+   pip install pyinstaller==6.3.0
+   choco install innosetup -y
+   ```
+2. Bundle the application:
+   ```powershell
+   pyinstaller --name RestormerServer --onefile --add-data "app;app" app/main.py
+   ```
+3. Use the provided `installer/innosetup.iss` script to build a GUI installer
+   with Inno Setup (script included under `server/installer`).
+
+## Production Notes
+
+- Configure a reverse proxy (e.g. Nginx or Caddy) with HTTPS termination.
+- Set environment variables `RESTORMER_SECRET_KEY`, `GOOGLE_CLIENT_ID`, and
+  `GOOGLE_CLIENT_SECRET` in production.
+- For persistent storage, use an external database (PostgreSQL) by updating the
+  `database_url` value in `.env`.
 
EOF
)
>>>>>>> origin/main
