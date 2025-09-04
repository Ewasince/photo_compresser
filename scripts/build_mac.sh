#!/usr/bin/env bash
set -euo pipefail

# Change to repository root
cd "$(dirname "$0")/.."

source .venv/bin/activate

pyside6-rcc resources/resources.qrc -o service/resources_rc.py

python -m nuitka service/main.py \
    --macos-create-app-bundle \
    --macos-app-name=photo_compresser \
    --enable-plugin=pyside6 \
    --include-qt-plugins=sensible,styles \
    --output-dir=dist

mv "dist/main.app" "dist/photo_compresser.app"
