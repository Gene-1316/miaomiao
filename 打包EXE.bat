@echo off
cd /d "%~dp0"
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    pause
    exit /b 1
)
python -m PyInstaller --noconfirm --workpath build/standalone miaomiao.spec
if errorlevel 1 (
    pause
    exit /b 1
)
echo Built: dist\miaomiao.exe
pause
