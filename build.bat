@echo off
REM Build script for Positron standalone executable
REM This script builds the application using PyInstaller

echo ========================================
echo Positron Build Script
echo ========================================
echo.

REM Clean previous build artifacts
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo.

REM Build the application
echo Building Positron executable...
echo This may take several minutes...
echo.
pyinstaller positron.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    echo If you see "pyinstaller is not recognized", install it with:
    echo   pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo The executable is located at:
echo   dist\Positron\Positron.exe
echo.
echo To distribute, copy the entire "dist\Positron" folder
echo to the target computer. The folder contains all required
echo libraries and dependencies.
echo.
echo IMPORTANT: The target computer must have:
echo   1. PicoScope drivers installed (PicoSDK)
echo   2. A compatible PicoScope device connected
echo.
pause
