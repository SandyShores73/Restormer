# PhoneAgent Host Controller

Electron macOS shell for configuring and testing the `phoneagentd`
tailnet gateway. It includes:

- Gateway URL and bearer token settings.
- Connection test and quick actions.
- Latency profiles with speed/battery/privacy trade-off descriptions.
- Natural-break voice interjection portal request UI.

## Development

```bash
cd client
npm install
npm run start
```

## Build and package

The app includes a committed static renderer for packaging. On macOS, package the app with:

```bash
npm run package:mac-dir
npm run build
```

Linux CI can validate JSON/JavaScript syntax, but DMG creation requires macOS and an installable npm registry.
