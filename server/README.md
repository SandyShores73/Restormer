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

Create a `.env` file (optional) to override configuration values such as the
JWT secret key or allowed CORS origins.

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
- Set environment variables `RESTORMER_SECRET_KEY`, `GOOGLE_CLIENT_ID`, and
  `GOOGLE_CLIENT_SECRET` in production.
- For persistent storage, use an external database (PostgreSQL) by updating the
  `database_url` value in `.env`.
