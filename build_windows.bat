@echo off
REM Build script for Windows (OpenCode Token Meter)
REM Uses unified spec file to build single executable

echo ========================================
echo Building OpenCode Token Meter for Windows
echo ========================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Check PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Check PyQt6
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing PyQt6...
    pip install PyQt6
)

echo.
echo Building unified app (Agent + Menubar)...
echo Using spec file: OpenCodeTokenMeter.spec
echo.

REM Build using the unified spec file
echo.
echo Checking icon file...
if exist "App\menubar\resources\AppIcon.ico" (
    echo Icon found: App\menubar\resources\AppIcon.ico
) else (
    echo WARNING: Icon file not found!
)
echo.

pyinstaller --clean OpenCodeTokenMeter.spec

if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executable location:
echo   dist\OpenCodeTokenMeter.exe
echo.
echo This is a single unified app containing:
echo   - Menubar UI with system tray icon
echo   - Agent module (embedded)
echo   - Application icon
echo.
echo To run:
echo   dist\OpenCodeTokenMeter.exe
echo.
pause
