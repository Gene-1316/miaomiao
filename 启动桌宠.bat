@echo off
cd /d "%~dp0"
python -c "import PySide6, PIL, numpy, cv2" >nul 2>nul
if errorlevel 1 (
    echo Installing Python dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Please install Python 3.10 or newer and enable Add Python to PATH.
        pause
        exit /b 1
    )
)
start "" pythonw.exe "%~dp0main.py"
