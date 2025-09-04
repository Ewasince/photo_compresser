@echo off
setlocal

REM Change to repository root

call ".venv\Scripts\activate.bat"

pyside6-rcc resources\resources.qrc -o service\resources_rc.py

python -m nuitka service\main.py ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --windows-console-mode=disable ^
    --include-qt-plugins=sensible,styles ^
    --windows-icon-from-ico=resources\bp.ico ^
    --output-dir=dist

move "dist\main.exe" "dist\photo_compresser.exe"
