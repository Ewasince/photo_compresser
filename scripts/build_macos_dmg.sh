#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/.venv/bin/activate"

python -m nuitka "$ROOT_DIR/service/main.py" \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=sensible,styles \
    --macos-app-icon="$ROOT_DIR/resources/bp.icns" \
    --macos-app-name=PhotoCompresser \
    --output-dir="$ROOT_DIR/dist"

APP_PATH="$ROOT_DIR/dist/PhotoCompresser.app"
if [ -d "$APP_PATH" ]; then
    hdiutil create "$ROOT_DIR/dist/photo_compresser.dmg" -srcfolder "$APP_PATH"
fi
