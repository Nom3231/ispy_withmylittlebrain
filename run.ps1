Set-Location $PSScriptRoot
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🕹️  Starting I Spy With My Little Brain Server..." -ForegroundColor Yellow
Write-Host "🌐  Opening at http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" run.py
