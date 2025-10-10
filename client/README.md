# Restormer Remote Client

Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
communicates with the Restormer Remote AI denoise server.

## Development

From the repository root run **exactly once**:

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

## macOS Installation

1. Build the DMG on macOS (or download the generated `Restormer-Remote-Client-*.dmg`
   artifact if you already ran `npm run build`).
2. Double-click the DMG to mount it and drag **Restormer Remote Client.app** into
   your **Applications** folder.
3. Launch the app from Applications. On first run macOS may warn that the
   application was downloaded from the internet—choose **Open** to continue.
4. When prompted, supply your server URL (or keep the default if you are running
   the backend locally) and sign in with the credentials that were provisioned on
   the server.

> **Tip:** After installation you can eject the mounted DMG from Finder. Future
> updates only require replacing the app inside Applications.
