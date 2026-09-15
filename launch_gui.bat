@echo off
echo Starting ATX-Converter...

REM Check if running from dist (exe mode) or source (python mode)
if exist "%~dp0ATX-Converter.exe" (
    start "" "%~dp0ATX-Converter.exe"
    exit /b
)

REM Fallback: run from Python source
if exist "%~dp0pcc_convertor.py" (
    python "%~dp0pcc_convertor.py"
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to start. Make sure Python 3.8+ is installed.
        echo Install dependencies: pip install -r requirements.txt
        pause
    )
) else (
    echo ERROR: Neither ATX-Converter.exe nor pcc_convertor.py found.
    echo Please run this from the ATX-Converter directory.
    pause
)
