@echo off
title CyberAware AI - Enterprise Security Operations Center
cls
echo =====================================================================
echo    CYBERAWARE AI: AI Phishing Detection & Employee Awareness SOC
echo =====================================================================
echo.

set PYTHON_BIN=python

where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
        set PYTHON_BIN="%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    ) else (
        echo [ERROR] Python not found on PATH. Please install Python 3.10+ or add it to PATH.
        pause
        exit /b 1
    )
)

echo [*] Starting CyberAware AI Server on http://127.0.0.1:5000 ...
echo [*] Press CTRL+C to terminate the server.
echo.

%PYTHON_BIN% app.py
pause
