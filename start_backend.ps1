# PowerShell script to start the backend API server
Write-Host "Starting Content Creation Crew API Server..." -ForegroundColor Cyan
Write-Host ""

# Check if port 8000 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "Warning: Port 8000 is already in use!" -ForegroundColor Yellow
    Write-Host "You may need to stop the existing process first." -ForegroundColor Yellow
    Write-Host ""
}

# Start the server
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

uv run python api_server.py

