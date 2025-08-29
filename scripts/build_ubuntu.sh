#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/.venv/bin/activate"

python -m nuitka "$ROOT_DIR/service/main.py" \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=sensible,styles \
    --output-dir="$ROOT_DIR/dist"

mv "$ROOT_DIR/dist/main.bin" "$ROOT_DIR/dist/photo_compresser"
