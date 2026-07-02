@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Starting backend on http://127.0.0.1:8000 ...
start "Companion Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo Starting frontend on http://127.0.0.1:3000 ...
cd /d "%~dp0frontend"
if not exist "node_modules\" (
    echo Installing npm dependencies...
    call npm install
)
start "Companion Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Done. Open in browser: http://127.0.0.1:3000
echo Two new windows should open (Backend + Frontend). Keep them running.
pause
