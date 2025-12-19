# Start script for Web UI (Windows PowerShell)

Write-Host "Starting Content Creation Crew Web UI..." -ForegroundColor Cyan
Write-Host ""

# Start FastAPI backend in background
Write-Host "Starting FastAPI backend server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; uv run python api_server.py" -WindowStyle Minimized

# Wait for backend to start
Start-Sleep -Seconds 3

# Start Next.js frontend
Write-Host "Starting Next.js frontend..." -ForegroundColor Yellow
Set-Location web-ui
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev"

Write-Host ""
Write-Host "✅ Both servers are starting!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the opened PowerShell windows for server status" -ForegroundColor Yellow

