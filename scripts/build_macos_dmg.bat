@echo off
setlocal

REM Change to repository root
pushd "%~dp0\.."

call ".venv\Scripts\activate.bat"

python -m nuitka service\main.py ^
    --onefile ^
    --enable-plugin=pyside6 ^
    --include-qt-plugins=sensible,styles ^
    --macos-app-icon=resources\bp.icns ^
    --macos-app-name=PhotoCompresser ^
    --output-dir=dist

if exist "dist\PhotoCompresser.app" (
    hdiutil create "dist\photo_compresser.dmg" -srcfolder "dist\PhotoCompresser.app"
)

popd
