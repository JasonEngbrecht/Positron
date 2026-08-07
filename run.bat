@echo off
REM Run Positron from source (development)
REM Uses the py launcher (python is not on PATH on this machine)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py main.py
) else (
    python main.py
)

if errorlevel 1 (
    echo.
    echo Positron exited with an error. See messages above.
    pause
)
