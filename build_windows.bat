@echo off
REM Build script for Windows (OpenCode Token Meter)
REM Uses unified spec file to build single executable
setlocal enabledelayedexpansion

echo ========================================
echo    OpenCode Token Meter Build Script
echo ========================================

REM Best-effort cleanup for stale pyc cache that may be read-only/locked
set "STALE_PYCS=build\OpenCodeTokenMeter\localpycs"
if exist "%STALE_PYCS%" (
    echo  - Cleaning stale cache: %STALE_PYCS%
    attrib -r "%STALE_PYCS%" /s /d >nul 2>&1
    rmdir /s /q "%STALE_PYCS%" >nul 2>&1
    if exist "%STALE_PYCS%" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%STALE_PYCS%' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
    )
    if exist "%STALE_PYCS%" (
        echo  - WARNING: Could not fully remove %STALE_PYCS% ^(likely in use^), continuing...
    ) else (
        echo  - Cache cleaned
    )
)

REM Best-effort cleanup for previous EXE that may be locked by running app
set "DIST_EXE=dist\OpenCodeTokenMeter.exe"
if exist "%DIST_EXE%" (
    echo  - Cleaning old executable: %DIST_EXE%
    attrib -r "%DIST_EXE%" >nul 2>&1
    del /f /q "%DIST_EXE%" >nul 2>&1
    if exist "%DIST_EXE%" (
        taskkill /f /im OpenCodeTokenMeter.exe >nul 2>&1
        timeout /t 1 /nobreak >nul 2>&1
        del /f /q "%DIST_EXE%" >nul 2>&1
    )
    if exist "%DIST_EXE%" (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath '%DIST_EXE%' -Force -ErrorAction SilentlyContinue" >nul 2>&1
    )
    if exist "%DIST_EXE%" (
        echo ERROR: Old executable is still locked ^(dist\OpenCodeTokenMeter.exe^).
        echo        Please close running OpenCode Token Meter and run build again.
        exit /b 1
    ) else (
        echo  - Old executable cleaned
    )
)

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

REM Pin setuptools to avoid win10toast/pkg_resources deprecation breakage
python -c "import setuptools,sys,re;m=re.match(r'(\d+)', setuptools.__version__);sys.exit(0 if m and int(m.group(1)) < 81 else 1)" >nul 2>&1
if errorlevel 1 (
    echo  - Pinning setuptools ^< 81 for Windows build compatibility...
    pip install --quiet "setuptools<81" >nul 2>&1
)

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

REM Re-assert setuptools pin in case dependency resolution upgraded it
python -c "import setuptools,sys,re;m=re.match(r'(\d+)', setuptools.__version__);sys.exit(0 if m and int(m.group(1)) < 81 else 1)" >nul 2>&1
if errorlevel 1 (
    echo  - Re-pinning setuptools ^< 81...
    pip install --quiet "setuptools<81" >nul 2>&1
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
set "PYTHONWARNINGS=ignore:pkg_resources is deprecated as an API:UserWarning"
pyinstaller --clean --noconfirm --log-level=ERROR OpenCodeTokenMeter.spec > "%TEMP_LOG%" 2>&1
set "PYTHONWARNINGS="

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
