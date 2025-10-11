# Restormer Remote Client

Electron + React desktop client for macOS (DMG) and Windows (NSIS EXE) that
communicates with the Restormer Remote AI denoise server.

The refreshed client ships with an Apple-inspired adaptive UI, animated
loading screen, GPU job progress visualisations, live debugging console, and a
first-run onboarding flow that validates a user-selected username/password
against the server whitelist before enabling access. Every stage of the
Restormer batch pipeline (model caching, per-pass inference, archiving) emits
progress percentages so the macOS and Windows builds never appear “stuck” on a
blank screen.

## Development

From the repository root run **exactly once**:

```bash
cd client
npm install
npm run dev
```

> **Disk space requirements (macOS):** Installing the Electron runtime pulls
> down archives that temporarily consume ~2–3 GB. If `npm install` aborts with
> `ENOSPC: no space left on device` (or any error that prevents dependencies
> from being written to `node_modules`), free additional disk space, delete the
> partially created `client/node_modules` folder, and rerun `npm install`. Any
> subsequent `cross-env: command not found` messages are a side effect of the
> failed install—once the dependency install succeeds, `cross-env` will be
> available to `npm run dev`.

> **Note:** If you previously attempted a merge that left conflict markers
> (e.g. `<<<<<<< HEAD`) inside `package.json`, resolve them or reset the file
> before running `npm install`.  You can restore the clean version with
> `git checkout -- package.json`.

By default the renderer points to `http://localhost:8000`. Set
`VITE_API_BASE=https://your-public-domain` before `npm run dev` to use a remote
server. Inside the app, open the **Server Connection** panel to store any
publicly reachable base URL—the value is persisted locally so packaged builds
can connect to your production endpoint without recompilation.

## Feature tour

- **Luminescent splash & loading overlay** – the app now opens with a full
  screen glassmorphism splash that animates progress as the desktop client
  restores settings, probes `/health`, and validates saved sessions. Signing in
  reuses the same overlay so users never experience a white blank window.
- **Onboarding with whitelist verification** – first-time operators can pick
  their username (email) and password and press “Check whitelist”. The client
  hits the new `/users/verify` endpoint before presenting password fields so
  only approved accounts proceed. Successful registration flows straight into a
  secured session without restarting the app.
- **Auto-scaling Apple-esque layout** – gradient backgrounds, rounded glass
  cards, and adaptive typography scale from 13" laptops through 4K displays.
  Status chips and “image cues” (animated gradient glyphs) provide at-a-glance
  feedback for each job state.
- **Live pipeline telemetry** – the job timeline now ships with progress bars
  fed by the server’s stage-by-stage metrics. Selecting a job reveals the full
  debug log, while the “Active debugging feed” card streams the latest messages
  across all jobs so power users can triage issues quickly.
- **Upload progress & refetch cues** – file uploads emit realtime percentages
  and the dashboard shows when the client is refreshing job telemetry, making
  long GPU runs predictable.
- **Restormer mode matrix & bulk batching** – choose between denoising, motion
  deblur, or defocus correction, control 1x–5x passes, and queue up to 25
  images in a single batch with automatic archive downloads.

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
   the backend locally). The onboarding flow will let you verify your email is
   whitelisted, pick a password, and watch the animated loading screen connect
   you to the GPU cockpit.

> **Tip:** After installation you can eject the mounted DMG from Finder. Future
> updates only require replacing the app inside Applications.
