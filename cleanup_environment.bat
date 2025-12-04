@echo off
REM Quick cleanup script for pathlib issues

echo ====================================
echo OBS Installer Environment Cleanup
echo ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Run the Python cleanup script
python cleanup_environment.py

echo.
echo Cleanup completed. You can now run build_installer.bat
pause