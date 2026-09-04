@echo off
REM Build script for Positron standalone executable
REM This script builds the application using PyInstaller

echo ========================================
echo Positron Build Script
echo ========================================
echo.

REM Generate PDF user manual
echo Generating user manual PDF...
REM Prefer the py launcher: on some machines plain `python` is only the
REM Microsoft Store stub, which fails and leaves the manual stale.
where py >nul 2>nul
if %errorlevel% equ 0 (
    py generate_readme_pdf.py
    if errorlevel 1 (
        echo WARNING: Failed to generate PDF user manual
        echo Make sure reportlab is installed: pip install reportlab
        echo Continuing with build anyway...
        echo.
    )
) else (
    REM Fall back to python on PATH
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        python generate_readme_pdf.py
        if errorlevel 1 (
            echo WARNING: Failed to generate PDF user manual
            echo Make sure reportlab is installed: pip install reportlab
            echo Continuing with build anyway...
            echo.
        )
    ) else (
        echo WARNING: Python not found in PATH
        echo PDF user manual will not be generated
        echo To fix: Add Python to your PATH or install reportlab: pip install reportlab
        echo Continuing with build anyway...
        echo.
    )
)
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

REM Remove the intermediate bootloader stub PyInstaller leaves in build\.
REM It has no _internal\ folder beside it, so launching it fails with
REM "Failed to load Python DLL". Only dist\Positron\Positron.exe is runnable.
if exist "build\positron\Positron.exe" del /q "build\positron\Positron.exe"

REM Copy PDF to distribution folder
if exist "Positron_User_Manual.pdf" (
    echo.
    echo Copying user manual to distribution folder...
    copy "Positron_User_Manual.pdf" "dist\Positron\Positron_User_Manual.pdf"
    echo.
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo The executable is located at:
echo   dist\Positron\Positron.exe
echo (Do not run anything under build\ - that folder holds only intermediates.)
echo.
echo User manual included at:
echo   dist\Positron\Positron_User_Manual.pdf
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
