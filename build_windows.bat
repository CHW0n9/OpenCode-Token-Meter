@echo off
REM Build script for Windows (OpenCode Token Meter)
REM Uses unified spec file to build single executable
setlocal enabledelayedexpansion

echo ========================================
echo    OpenCode Token Meter Build Script
echo ========================================

REM Check Python
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
if "%PYVER%"=="" (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)
echo  - Python: %PYVER%

REM Check dependencies
echo.
echo [1/3] Checking dependencies...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  - Installing PyInstaller...
    pip install --quiet pyinstaller >nul 2>&1
)

python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo  - Installing pywebview...
    pip install --quiet pywebview >nul 2>&1
)

python -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo  - Installing pystray...
    pip install --quiet pystray >nul 2>&1
)

python -c "import PIL" >nul 2>&1
if errorlevel 1 (
    echo  - Installing pillow...
    pip install --quiet pillow >nul 2>&1
)

python -c "import pyperclip" >nul 2>&1
if errorlevel 1 (
    echo  - Installing pyperclip...
    pip install --quiet pyperclip >nul 2>&1
)

python -c "import win10toast" >nul 2>&1
if errorlevel 1 (
    echo  - Installing win10toast...
    pip install --quiet win10toast >nul 2>&1
)
 echo  - Dependencies OK

REM Check resources
echo.
echo [2/3] Checking resources...
if exist "App\webview_ui\web\assets\AppIcon.ico" (
    echo  - Icon OK
) else (
    echo  - WARNING: Icon file not found!
)

REM Build application
echo.
echo [3/3] Building application...
echo  - This may take a moment...

REM Create temp file for output
set TEMP_LOG=%TEMP%\pyinstaller_build.log

REM Build using the unified spec file with reduced verbosity
pyinstaller --clean --noconfirm --log-level=ERROR OpenCodeTokenMeter.spec > "%TEMP_LOG%" 2>&1

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. See log:
    type "%TEMP_LOG%" | findstr /i "error" 
    del "%TEMP_LOG%" >nul 2>&1
    exit /b 1
)

REM Show key info from log
for /f "tokens=2,* delims=:" %%a in ('findstr /r "^[0-9]* INFO:" "%TEMP_LOG%" 2^>nul') do (
    echo  -%%b
    goto :done_info
)
:done_info
del "%TEMP_LOG%" >nul 2>&1

REM Check if exe was created and get size
if not exist "dist\OpenCodeTokenMeter.exe" (
    echo ERROR: Executable not created
    exit /b 1
)

for %%A in ("dist\OpenCodeTokenMeter.exe") do set EXE_SIZE=%%~zA
set /a EXE_SIZE_MB=%EXE_SIZE% / 1048576
echo  - Executable: %EXE_SIZE_MB%MB

echo.
echo ========================================
echo            Build Complete!
echo ========================================
echo  App: %EXE_SIZE_MB%MB -^> dist\OpenCodeTokenMeter.exe
echo.
pause
