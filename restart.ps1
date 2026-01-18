# Restart script for Windows after fixes

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Restarting LinkedIn AI Manager" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Stop any running instances
Write-Host "Stopping any running instances..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*LinkedIn*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Wait a moment
Start-Sleep -Seconds 2

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Run the application
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Starting LinkedIn AI Manager..." -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python run_all.py
