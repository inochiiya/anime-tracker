@echo off
setlocal
title Anime Tracker
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_ARGS="
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "ANIME_PORT=18101"
set "ANIME_BROWSER_URL=http://127.0.0.1/apps/anime/"
set "ANIME_DIRECT_URL=http://127.0.0.1:18101/"
if /I "%~1"=="--no-browser" (
    set "ANIME_OPEN_BROWSER=0"
) else if not defined ANIME_OPEN_BROWSER (
    set "ANIME_OPEN_BROWSER=1"
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE goto :no_python

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto :old_python

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import fastapi, uvicorn, sqlalchemy, pydantic, multipart, httpx" >nul 2>&1
if errorlevel 1 (
    echo Required packages are missing. Installing from backend\requirements.txt...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install -r backend\requirements.txt
    if errorlevel 1 goto :install_failed
    echo.
)

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort 18101 -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 goto :port_in_use

if "%ANIME_OPEN_BROWSER%"=="1" (
    start "" /b powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(60); do { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18101/api/stats' -TimeoutSec 2; if ($r.StatusCode -eq 200) { $target=$env:ANIME_DIRECT_URL; try { $site=Invoke-WebRequest -UseBasicParsing -Uri $env:ANIME_BROWSER_URL -TimeoutSec 2; if ($site.StatusCode -eq 200) { $target=$env:ANIME_BROWSER_URL } } catch {}; Start-Process $target; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $deadline)"
)

echo Starting Anime Tracker...
echo App:  http://127.0.0.1:18101
echo Site: http://127.0.0.1/apps/anime/
echo Press Ctrl+C to stop.
echo.

pushd backend
"%PYTHON_EXE%" %PYTHON_ARGS% -m uvicorn main:app --host 127.0.0.1 --port %ANIME_PORT%
set "EXIT_CODE=%errorlevel%"
popd
if not "%EXIT_CODE%"=="0" echo Service exited with code %EXIT_CODE%.
goto :finish

:port_in_use
echo Port 18101 is already in use. Stop the existing service or choose another registered port.
set "EXIT_CODE=1"
goto :finish

:no_python
echo Python was not found. Install Python 3.10 or newer and try again.
set "EXIT_CODE=1"
goto :finish

:old_python
echo Python 3.10 or newer is required.
set "EXIT_CODE=1"
goto :finish

:install_failed
echo Failed to install required packages. Check your network and pip configuration.
set "EXIT_CODE=1"

:finish
echo.
pause
endlocal & exit /b %EXIT_CODE%
