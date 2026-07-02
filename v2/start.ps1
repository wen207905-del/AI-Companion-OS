# AI Companion OS V2 — 一键启动后端 + 前端
# 用法（PowerShell）: .\start.ps1
# 用法（CMD）: start.bat
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "cd /d `"$Root\backend`" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://127.0.0.1:3000 ..." -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "cd /d `"$Root\frontend`" && npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "Done. Open: http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Two windows opened (Backend + Frontend). Keep them running." -ForegroundColor Green
