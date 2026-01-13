# cleanup_outdated_md_files.ps1
# Safe cleanup script with dry-run option

param(
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Markdown File Cleanup Script" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "DRY RUN MODE - No files will be deleted" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define files to remove
$filesToRemove = @(
    "RAILWAY_CRITICAL_FIX.md",
    "RAILWAY_DATABASE_CONNECTION_FIX.md",
    "RAILWAY_BUILD_FIX.md",
    "RAILWAY_ROOT_DIRECTORY_FIX.md",
    "RAILWAY_STARTUP_TROUBLESHOOTING.md",
    "RAILWAY_DEPLOYMENT.md",
    "RAILWAY_DEPLOYMENT_CHECKLIST.md",
    "RAILWAY_AUTO_DEPLOY_SETUP.md",
    "RAILWAY_LINK_DATABASE.md",
    "CHECKOUT_ERROR_FIX.md",
    "POOL_DO_GET_FIX.md",
    "POOL_ERROR_FIX.md",
    "DATABASE_POOL_FIX.md",
    "DATABASE_CONNECTION_FIX.md",
    "DATABASE_CONNECTION_VERIFICATION.md",
    "VERIFY_DATABASE_CONNECTION.md",
    "FRONTEND_502_FIX.md",
    "FRONTEND_502_FIX_FINAL.md",
    "FRONTEND_BACKEND_CONNECTION.md",
    "FRONTEND_DEPLOYMENT_FIX.md",
    "FRONTEND_FIX_COMPLETE.md",
    "FRONTEND_RAILWAY_DEPLOYMENT.md",
    "DEBUG_STARTUP.md",
    "DEBUG_STREAMING.md",
    "SIGNUP_DEBUG.md",
    "QUICK_STARTUP_FIX.md",
    "APPLICATION_RESTART_DEBUG.md",
    "APPLICATION_SHUTDOWN_DEBUG.md",
    "502_ERROR_FIX.md",
    "HEALTH_CHECK_FIX.md",
    "API_URL_FIX.md",
    "FIX_ENV_FILE.md",
    "PORT_CONSISTENCY_REPORT.md",
    "content_output.md",
    "video_output.md",
    "audio_output.md",
    "social_media_output.md",
    "AUTHENTICATION_SETUP.md",
    "OAUTH_SETUP.md",
    "QUICK_START_OAUTH.md",
    "WEB_UI_SETUP.md",
    "START_SERVERS.md",
    "DATABASE_MIGRATIONS.md"
)

# Check which files exist
$existingFiles = $filesToRemove | Where-Object { Test-Path $_ }

if ($existingFiles.Count -eq 0) {
    Write-Host "No files to remove!" -ForegroundColor Green
    exit 0
}

# Show files that will be deleted
Write-Host "Files to be deleted ($($existingFiles.Count)):" -ForegroundColor Yellow
Write-Host "-------------------" -ForegroundColor Yellow
foreach ($file in $existingFiles) {
    $fileInfo = Get-Item $file
    $size = "{0:N2} KB" -f ($fileInfo.Length / 1KB)
    Write-Host "  - $file" -ForegroundColor White
    Write-Host "    Size: $size | Modified: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
}
Write-Host ""

# Calculate total size
$totalSize = ($existingFiles | Get-Item | Measure-Object -Property Length -Sum).Sum
$totalSizeMB = "{0:N2}" -f ($totalSize / 1MB)
Write-Host "Total size to free: $totalSizeMB MB" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN: No files were deleted. Run without -DryRun to delete." -ForegroundColor Yellow
    exit 0
}

# Confirmation prompt (unless Force is used)
if (-not $Force) {
    Write-Host "========================================" -ForegroundColor Cyan
    $confirmation = Read-Host "Do you want to delete these files? (yes/no)"
    
    if ($confirmation -ne "yes") {
        Write-Host "Cleanup cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Delete files
Write-Host ""
Write-Host "Deleting files..." -ForegroundColor Cyan
$deletedCount = 0
$errorCount = 0
$deletedSize = 0

foreach ($file in $existingFiles) {
    try {
        $fileInfo = Get-Item $file
        $fileSize = $fileInfo.Length
        
        Remove-Item $file -Force
        Write-Host "  Deleted: $file" -ForegroundColor Green
        $deletedCount++
        $deletedSize += $fileSize
    } catch {
        Write-Host "  Error deleting $file : $_" -ForegroundColor Red
        $errorCount++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Files deleted: $deletedCount" -ForegroundColor Green
$spaceFreed = "{0:N2}" -f ($deletedSize / 1MB)
Write-Host "Space freed: $spaceFreed MB" -ForegroundColor Green
if ($errorCount -eq 0) {
    Write-Host "Errors: $errorCount" -ForegroundColor Green
} else {
    Write-Host "Errors: $errorCount" -ForegroundColor Red
}
Write-Host ""

if ($deletedCount -gt 0) {
    Write-Host "Cleanup completed successfully!" -ForegroundColor Green
}
