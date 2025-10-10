# Restormer Remote Client

Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
communicates with the Restormer Remote AI denoise server.

## Development

```bash
cd client
npm install
npm run dev
```

The dev server expects the FastAPI backend to be running at
`http://localhost:8000`.  Override by setting `VITE_API_BASE` before running Vite.

## Production Builds

- **macOS:** `npm run build` produces a signed DMG (signing identity required).
- **Windows:** run the build on Windows to generate an `.exe` installer.

The Electron builder configuration in `package.json` outputs installers to the
`dist/` directory.
