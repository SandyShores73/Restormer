<<<<<<< HEAD
# Restormer Remote Client

Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
communicates with the Restormer Remote AI denoise server.

## Development

From the repository root run:

```bash
cd client
npm install
npm run dev
```

> **Note:** If you previously attempted a merge that left conflict markers
> (e.g. `<<<<<<< HEAD`) inside `package.json`, resolve them or reset the file
> before running `npm install`.  You can restore the clean version with
> `git checkout -- package.json`.

By default the renderer points to `http://localhost:8000`.  Set
`VITE_API_BASE=https://your-public-domain` before `npm run dev` to use a remote
server.  Inside the app, open the **Server Connection** panel to store any
publicly reachable base URL—the value is persisted locally so packaged builds
can connect to your production endpoint without recompilation.

## Production Builds

- **macOS:** `npm run build` produces a signed DMG (signing identity required).
- **Windows:** run the build on Windows to generate an `.exe` installer.

The Electron builder configuration in `package.json` outputs installers to the
`dist/` directory.
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/README.md
index 0000000000000000000000000000000000000000..e351586f1bc7ada547f588611ee6bb30f41ec31b 100644
--- a//dev/null
+++ b/client/README.md
@@ -0,0 +1,23 @@
+# Restormer Remote Client
+
+Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
+communicates with the Restormer Remote AI denoise server.
+
+## Development
+
+```bash
+cd client
+npm install
+npm run dev
+```
+
+The dev server expects the FastAPI backend to be running at
+`http://localhost:8000`.  Override by setting `VITE_API_BASE` before running Vite.
+
+## Production Builds
+
+- **macOS:** `npm run build` produces a signed DMG (signing identity required).
+- **Windows:** run the build on Windows to generate an `.exe` installer.
+
+The Electron builder configuration in `package.json` outputs installers to the
+`dist/` directory.
 
EOF
)
>>>>>>> origin/main
