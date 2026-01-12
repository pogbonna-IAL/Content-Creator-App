# FFmpeg installation script for Windows PowerShell

Write-Host "FFmpeg Installation Script" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Check if FFmpeg is already installed
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "[OK] FFmpeg is already installed!" -ForegroundColor Green
    ffmpeg -version | Select-Object -First 1
    exit 0
}

Write-Host "FFmpeg not found. Checking for package managers..." -ForegroundColor Yellow
Write-Host ""

# Check for Chocolatey
if (Get-Command choco -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] Found Chocolatey" -ForegroundColor Green
    $install = Read-Host "Install FFmpeg using Chocolatey? (Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Write-Host "Installing FFmpeg using Chocolatey..." -ForegroundColor Cyan
        choco install ffmpeg -y
        Write-Host "[OK] FFmpeg installed!" -ForegroundColor Green
        exit 0
    }
}

# Check for winget
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] Found winget" -ForegroundColor Green
    $install = Read-Host "Install FFmpeg using winget? (Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Write-Host "Installing FFmpeg using winget..." -ForegroundColor Cyan
        winget install ffmpeg
        Write-Host "[OK] FFmpeg installed!" -ForegroundColor Green
        exit 0
    }
}

# Manual installation instructions
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Yellow
Write-Host "Manual Installation Required" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor White
Write-Host "2. Extract the zip file" -ForegroundColor White
Write-Host "3. Add the 'bin' folder to your system PATH:" -ForegroundColor White
Write-Host "   - Open System Properties > Environment Variables" -ForegroundColor White
Write-Host "   - Edit PATH variable" -ForegroundColor White
Write-Host "   - Add: C:\path\to\ffmpeg\bin" -ForegroundColor White
Write-Host ""
Write-Host "Or install a package manager:" -ForegroundColor White
Write-Host "  - Chocolatey: https://chocolatey.org/install" -ForegroundColor White
Write-Host "  - winget: Included with Windows 10/11" -ForegroundColor White
Write-Host ""

