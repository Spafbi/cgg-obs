@echo off
chcp 65001 >nul 2>&1

REM CGG OBS Studio Installer - Automated Setup and Launcher
REM 
REM This batch file automatically sets up the complete Python environment
REM and launches the CGG OBS Studio Installer on Windows.
REM 
REM Features:
REM - Automatically installs Python 3.13 via winget if needed
REM - Installs pip and pipenv if not available
REM - Sets up the pipenv virtual environment
REM - Runs the installer in the proper environment

echo =============================================
echo CGG OBS Studio Installer - Automated Setup
echo =============================================
echo.

REM Check if Python 3.13 is available
echo Checking Python installation...

REM Try python3 first, then python
python3 --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Python not found. Installing Python 3.13 via winget...
        goto install_python
    ) else (
        set PYTHON_CMD=python
    )
) else (
    set PYTHON_CMD=python3
)

REM Check Python version
for /f "tokens=2" %%a in ('%PYTHON_CMD% --version 2^>^&1') do set pyver=%%a
echo Found Python version: %pyver%

REM Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%pyver%") do (
    set major=%%a
    set minor=%%b
)

REM Check if version is adequate (simplified check)
if "%major%" LSS "3" (
    echo Python version %pyver% is too old. Need Python 3.13+
    goto install_python
)

if "%major%" EQU "3" (
    if "%minor%" LSS "13" (
        echo Python version %pyver% is too old. Need Python 3.13+
        goto install_python
    )
)

echo [OK] Python %pyver% is compatible
goto check_pip

:install_python
echo.
echo Installing Python 3.13 using winget...
echo This may take a few minutes...

REM Check if winget is available
winget --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: winget is not available on this system.
    echo Please install Python 3.13 manually from https://python.org
    echo Make sure to add Python to your PATH during installation.
    pause
    exit /b 1
)

REM Install Python 3.13 via winget
echo Running: winget install Python.Python.3.13...
winget install Python.Python.3.13 --source winget --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
    echo ERROR: Failed to install Python via winget.
    echo Please install Python 3.13 manually from https://python.org
    pause
    exit /b 1
)

echo [OK] Python 3.13 installed successfully
echo.
echo NOTE: You may need to restart your command prompt for Python to be available.
echo If the script continues to fail, please restart and run install_obs.bat again.
echo.

REM Try to find Python again
python3 --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Python still not found in PATH.
        echo Please restart your command prompt and run install_obs.bat again.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python
    )
) else (
    set PYTHON_CMD=python3
)

:check_pip
echo.
echo Checking pip installation...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Installing pip...
    %PYTHON_CMD% -m ensurepip --upgrade
    if errorlevel 1 (
        echo ERROR: Failed to install pip
        pause
        exit /b 1
    )
)
echo [OK] pip is available

:check_pipenv
echo.
echo Checking pipenv installation...
%PYTHON_CMD% -m pipenv --version >nul 2>&1
if errorlevel 1 (
    echo Installing pipenv...
    %PYTHON_CMD% -m pip install --user pipenv
    if errorlevel 1 (
        echo ERROR: Failed to install pipenv
        pause
        exit /b 1
    )
)
echo [OK] pipenv is available

:setup_environment
echo.
echo Setting up virtual environment...
echo This may take a few minutes on first run...

REM Install dependencies using pipenv
%PYTHON_CMD% -m pipenv install
if errorlevel 1 (
    echo ERROR: Failed to set up virtual environment
    echo This could be due to missing dependencies or network issues.
    pause
    exit /b 1
)

echo [OK] Virtual environment ready

:run_installer
echo.
echo =============================================
echo Starting CGG OBS Studio Installer
echo =============================================
echo.

REM Run the installer in the pipenv environment
%PYTHON_CMD% -m pipenv run python run_installer.py

REM Check the exit code
if errorlevel 1 (
    echo.
    echo Installation failed or was cancelled.
    echo Check the log file for details: %USERPROFILE%\obs_installer.log
) else (
    echo.
    echo Installation completed successfully!
)

echo.
echo Press any key to exit...
pause >nul