# Restormer Remote Client

Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
communicates with the Restormer Remote AI denoise server.

## Development

```bash
cd client
npm install
npm run dev
```

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
