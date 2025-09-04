@echo off
setlocal

REM Change to repository root

call ".venv\Scripts\activate.bat"

python -m nuitka service\main.py ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --include-qt-plugins=sensible,styles ^
    --windows-icon-from-ico=resources\bp.ico ^
    --include-data-files=resources\bp.ico=resources\bp.ico ^
    --output-dir=dist

move "dist\main.exe" "dist\photo_compresser.exe"
