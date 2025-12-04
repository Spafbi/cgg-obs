@echo off
REM OBS Installer Build Script
REM Creates a self-contained Windows executable using PyInstaller

echo ====================================
echo OBS Installer - Build Script
echo ====================================
echo.

REM Check if we're in the right directory
if not exist "obs_installer.spec" (
    echo ERROR: obs_installer.spec not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.13+ and try again.
    pause
    exit /b 1
)

echo Checking Python version...
python -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
echo.

REM Clean up environment issues
echo Checking for environment issues...
python cleanup_environment.py
if errorlevel 1 (
    echo ERROR: Environment cleanup failed
    echo Please resolve the issues reported above
    pause
    exit /b 1
)
echo.

REM Clean up any previous builds
echo Cleaning up previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"
echo.

REM Run PyInstaller with our spec file
echo Building executable with PyInstaller...
echo This may take several minutes...
echo.

REM Verify required files exist before building
echo Checking for required files...
if not exist "icons" (
    echo WARNING: icons directory not found!
    echo Please ensure the icons directory exists in the project root.
) else (
    echo ✓ Icons directory found
    dir "icons" /b | find /c /v "" > temp_count.txt
    set /p icon_count=<temp_count.txt
    del temp_count.txt
    setlocal enabledelayedexpansion
    echo   Contains !icon_count! files
    endlocal
)

if not exist "plugins.json" (
    echo WARNING: plugins.json not found!
    echo Please ensure plugins.json exists in the project root.
) else (
    echo ✓ plugins.json found
)

echo.
echo Starting PyInstaller build...

REM Run debug script to verify data files
echo Running pre-build diagnostics...
python debug_bundle.py
echo.

pyinstaller obs_installer.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the output above for error details.
    pause
    exit /b 1
)

echo.
echo ====================================
echo BUILD SUCCESSFUL!
echo ====================================
echo.

REM Check if the executable was created
if exist "dist\OBS_Installer\OBS_Installer.exe" (
    echo Executable created: dist\OBS_Installer\OBS_Installer.exe
    echo.
    
    REM Show file size
    for %%I in ("dist\OBS_Installer\OBS_Installer.exe") do echo File size: %%~zI bytes
    echo.
    
    REM List the contents of the distribution directory
    echo Distribution directory contents:
    dir "dist\OBS_Installer" /b
    echo.
    
    REM Check for bundled data files in _internal directory
    echo Verifying bundled resources:
    if exist "dist\OBS_Installer\_internal\icons" (
        echo ✓ Icons directory found in _internal
    ) else (
        echo ✗ Icons directory missing from _internal
    )
    
    if exist "dist\OBS_Installer\_internal\plugins.json" (
        echo ✓ plugins.json found in _internal
    ) else (
        echo ✗ plugins.json missing from _internal
    )
    echo.
    
    echo The self-contained executable is ready for distribution!
    echo You can copy the entire "dist\OBS_Installer" folder to any Windows system.
    echo.
    
) else (
    echo ERROR: Executable was not created!
    echo Check the build output for errors.
)

echo.
echo Build script completed.
pause