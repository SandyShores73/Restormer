# Packaging PhoneAgent Host Controller for macOS

This app is configured for `electron-builder` with product name **PhoneAgent Host
Controller**. The Electron main process loads the committed `renderer/` bundle, so packaging does not require a Vite build step.

## macOS packaging commands

```bash
cd client
npm install
npm run package:mac-dir
npm run build
```

- `package:mac-dir` creates an unpacked `.app` for local smoke testing.
- `build` creates a DMG when run on macOS.
- DMG signing/notarization requires Apple Developer credentials and should be done
  outside this Linux CI container.

## Current environment note

In this container, `npm install` is blocked by registry policy (`403 Forbidden`),
and DMG creation requires macOS. The source, package metadata, and scripts are
ready for packaging on the target Mac once dependencies can be installed.
