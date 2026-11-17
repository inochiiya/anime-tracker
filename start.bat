@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0backend"
if errorlevel 1 (
    echo [ERROR] Cannot enter backend directory
    pause
    exit /b 1
)
echo ========================================
echo    Anime Tracker - Starting...
echo ========================================

REM Kill any existing process on port 8000
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Port 8000 is in use by PID %%a, killing...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [1/2] Installing Python dependencies...
pip install -r requirements.txt -q
echo [2/2] Starting server...
echo.
echo URL:      http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo ========================================


@REM  start http://localhost:8000
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(60); do { try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/stats' -TimeoutSec 2; if ($r.StatusCode -eq 200) { Start-Process 'http://localhost:8000'; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $deadline)"

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
