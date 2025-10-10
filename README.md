diff --git a/README.md b/README.md
index 2fd71e54e66570026acec18adabf27054740109d..73fb2b952c537c579bd83b373fe494c45187e52f 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,25 @@
-# Restormer
+# Restormer Remote Suite
+
+This repository contains a GPU-enabled remote denoise/detail refinement platform
+consisting of a FastAPI backend and an Electron-based desktop client for macOS
+and Windows.
+
+## Structure
+
+- `server/` – FastAPI application with DirectML-accelerated ONNX inference,
+  SQLite persistence, JWT authentication, and optional Google Sign-In support.
+- `client/` – Electron + React desktop client packaged as `.dmg` (macOS) and
+  `.exe` (Windows) via electron-builder.
+
+## Quick Start
+
+1. Follow `server/README.md` to configure the backend.
+2. Follow `client/README.md` to run/build the desktop client.
+
+## Deployment Notes
+
+- Host the backend on a Windows 11 workstation with the AMD RX 7800 XT to take
+  advantage of DirectML GPU acceleration.
+- Use HTTPS and secure password hashing in production environments.
+- Maintain the allowed users list through the `/users` API endpoints or by
+  seeding the SQLite database.
