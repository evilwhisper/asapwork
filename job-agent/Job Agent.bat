@echo off
setlocal EnableDelayedExpansion
title Job Agent
color 0A

set "DIR=%~dp0"
set "VENV=%DIR%.venv"
set "MARKER=%DIR%.setup_done"
set "PORT=8000"

echo.
echo  ==========================================
echo    Job Agent
echo  ==========================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python not found.
    echo  Downloading Python installer...
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe'"
    echo.
    echo  Install Python (tick "Add to PATH"), then run this file again.
    pause
    exit /b 1
)

:: ── Create virtualenv if missing ──────────────────────────────────────────────
if not exist "%VENV%\Scripts\activate.bat" (
    echo  [*] Creating virtual environment...
    python -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"

:: ── First-time setup ──────────────────────────────────────────────────────────
if not exist "%MARKER%" (
    echo  [*] First run — installing dependencies (this takes ~2 min)...
    echo.
    pip install -r "%DIR%requirements.txt" -q --no-warn-script-location
    if errorlevel 1 ( echo  [!] pip install failed. & pause & exit /b 1 )

    echo  [*] Installing Chromium for scraping...
    playwright install chromium
    if errorlevel 1 ( echo  [!] Playwright install failed. & pause & exit /b 1 )

    :: Build frontend if Node is available
    node --version >nul 2>&1
    if not errorlevel 1 (
        echo  [*] Building frontend UI...
        pushd "%DIR%frontend"
        call npm install --silent 2>nul
        call npm run build 2>nul
        popd
    ) else (
        echo  [!] Node.js not found — UI will not be available.
        echo      Download from https://nodejs.org/ then delete .setup_done and re-run.
    )

    echo. > "%MARKER%"
    echo.
    echo  [OK] Setup complete!
    echo.
)

:: ── Kill anything already on the port ─────────────────────────────────────────
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%PORT% "') do (
    taskkill /PID %%p /F >nul 2>&1
)

:: ── Start the server ──────────────────────────────────────────────────────────
echo  [*] Starting Job Agent on http://localhost:%PORT% ...
start "" /B uvicorn backend.main:app --port %PORT% --log-level warning

:: ── Wait for it to be ready ───────────────────────────────────────────────────
set /a "tries=0"
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://localhost:%PORT%/api/health >nul 2>&1
if errorlevel 1 (
    set /a "tries+=1"
    if !tries! lss 15 goto wait_loop
    echo  [!] Server did not start in time.
    pause
    exit /b 1
)

:: ── Open browser ──────────────────────────────────────────────────────────────
start http://localhost:%PORT%
echo  [OK] Job Agent is running at http://localhost:%PORT%
echo.
echo  Keep this window open. Close it to stop the server.
echo.

:: ── Keep alive ────────────────────────────────────────────────────────────────
:loop
timeout /t 5 /nobreak >nul
goto loop
