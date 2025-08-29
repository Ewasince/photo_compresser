@echo off
setlocal

REM Change to repository root
pushd "%~dp0\.."

call ".venv\Scripts\activate.bat"

python -m nuitka service\main.py ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --include-qt-plugins=sensible,styles ^
    --output-dir=dist

move "dist\main.bin" "dist\photo_compresser"

popd
