#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
INSTALL_ROOT=${1:-"${HOME}/Applications"}
APP_NAME="RestormerServer.app"
APP_DIR="${INSTALL_ROOT}/${APP_NAME}"
RESOURCES_DIR="${APP_DIR}/Contents/Resources"
MACOS_DIR="${APP_DIR}/Contents/MacOS"
SUPPORT_ROOT="${HOME}/Library/Application Support/RestormerServer"
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "${RESOURCES_DIR}" "${MACOS_DIR}" "${SUPPORT_ROOT}"

# Copy server source
rsync -a --delete "${REPO_ROOT}/server/" "${RESOURCES_DIR}/server/"

cat > "${APP_DIR}/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>CFBundleDisplayName</key>
    <string>Restormer Server</string>
    <key>CFBundleExecutable</key>
    <string>RestormerServer</string>
    <key>CFBundleIdentifier</key>
    <string>com.restormer.server</string>
    <key>CFBundleName</key>
    <string>Restormer Server</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
  </dict>
</plist>
PLIST

cat > "${MACOS_DIR}/RestormerServer" <<'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
APP_ROOT=$(cd "$(dirname "$0")/.." && pwd)
RESOURCES_DIR="$APP_ROOT/Resources"
SUPPORT_ROOT="${HOME}/Library/Application Support/RestormerServer"
VENV_DIR="$SUPPORT_ROOT/venv"
PYTHON_BIN=${PYTHON_BIN:-python3}

mkdir -p "$SUPPORT_ROOT"
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$RESOURCES_DIR/server/requirements.txt"
python - <<'PY'
import asyncio
from server.app.services.pipeline import pipeline
asyncio.run(pipeline.prepare_all_models())
PY
LOG_DIR="$SUPPORT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/restormer-server.log"
python -m uvicorn server.app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a "$LOG_FILE"
LAUNCH

chmod +x "${MACOS_DIR}/RestormerServer"

echo "Restormer macOS server app staged at ${APP_DIR}"
echo "Double-click the app to bootstrap dependencies and launch the FastAPI service."
