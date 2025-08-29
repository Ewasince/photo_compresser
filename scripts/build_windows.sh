#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/.venv/bin/activate"

python -m nuitka "$ROOT_DIR/service/main.py" \
    --onefile \
    --enable-plugin=pyside6 \
    --windows-console-mode=disable \
    --include-qt-plugins=sensible,styles \
    --windows-icon-from-ico="$ROOT_DIR/resources/bp.ico" \
    --output-dir="$ROOT_DIR/dist"

mv "$ROOT_DIR/dist/main.exe" "$ROOT_DIR/dist/photo_compresser.exe"
