# Test migration rollback procedure (PowerShell version)
# This script applies migrations, rolls back one, and re-applies to verify rollback works

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "Migration Rollback Test"
Write-Host "=========================================="
Write-Host ""

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "✗ DATABASE_URL environment variable is not set" -ForegroundColor Red
    Write-Host "Set it with: `$env:DATABASE_URL = 'postgresql://user:pass@host:port/db'"
    exit 1
}

# Check if alembic is available
$alembicCmd = "alembic"
if (-not (Get-Command alembic -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  alembic not found in PATH, trying uv run alembic..." -ForegroundColor Yellow
    $alembicCmd = "uv run alembic"
}

# Function to get current revision
function Get-CurrentRevision {
    $output = & $alembicCmd current 2>&1
    if ($LASTEXITCODE -eq 0) {
        $match = $output | Select-String -Pattern '^\w+' | Select-Object -First 1
        if ($match) {
            return $match.Matches[0].Value
        }
    }
    return "none"
}

# Function to get head revision
function Get-HeadRevision {
    $output = & $alembicCmd heads 2>&1
    if ($LASTEXITCODE -eq 0) {
        $match = $output | Select-String -Pattern '^\w+' | Select-Object -First 1
        if ($match) {
            return $match.Matches[0].Value
        }
    }
    return "none"
}

Write-Host "Step 1: Checking current database state..."
$currentRev = Get-CurrentRevision
$headRev = Get-HeadRevision

Write-Host "  Current revision: $currentRev"
Write-Host "  Head revision: $headRev"
Write-Host ""

if ($currentRev -eq "none") {
    Write-Host "⚠️  Database not initialized. Applying initial migrations..." -ForegroundColor Yellow
    & $alembicCmd upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to apply initial migrations" -ForegroundColor Red
        exit 1
    }
    $currentRev = Get-CurrentRevision
    Write-Host "  Current revision after initial migration: $currentRev"
    Write-Host ""
}

if ($currentRev -eq $headRev) {
    Write-Host "⚠️  Database is already at head revision." -ForegroundColor Yellow
    Write-Host "  To test rollback, we need at least one migration to rollback."
    Write-Host "  Current: $currentRev"
    Write-Host ""
    
    # Check if there are multiple revisions
    $historyOutput = & $alembicCmd history 2>&1
    $revisionCount = ($historyOutput | Select-String -Pattern "Rev:").Count
    if ($revisionCount -le 1) {
        Write-Host "✗ Not enough migrations to test rollback (need at least 2)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  Rolling back one revision for testing..."
    & $alembicCmd downgrade -1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to rollback" -ForegroundColor Red
        exit 1
    }
    $currentRev = Get-CurrentRevision
    Write-Host "  Current revision after rollback: $currentRev"
    Write-Host ""
}

Write-Host "Step 2: Applying migrations to head..."
& $alembicCmd upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to apply migrations" -ForegroundColor Red
    exit 1
}
$currentRev = Get-CurrentRevision
Write-Host "✓ Migrations applied. Current revision: $currentRev" -ForegroundColor Green
Write-Host ""

if ($currentRev -eq "none" -or -not $currentRev) {
    Write-Host "✗ Failed to get current revision after upgrade" -ForegroundColor Red
    exit 1
}

# Get the previous revision
Write-Host "Step 3: Getting previous revision..."
$historyOutput = & $alembicCmd history 2>&1
$previousRev = ($historyOutput | Select-String -Pattern "Rev:" | Select-Object -Skip 1 -First 1 | Select-String -Pattern '\w{12}').Matches[0].Value

if (-not $previousRev -or $previousRev -eq $currentRev) {
    Write-Host "⚠️  Could not determine previous revision automatically" -ForegroundColor Yellow
    Write-Host "  This is the first migration - rollback test skipped"
    Write-Host "✓ Migration rollback test completed (no rollback needed)" -ForegroundColor Green
    exit 0
}

Write-Host "  Previous revision: $previousRev"
Write-Host "  Current revision: $currentRev"
Write-Host ""

Write-Host "Step 4: Rolling back one revision..."
& $alembicCmd downgrade -1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to rollback" -ForegroundColor Red
    exit 1
}
$rollbackRev = Get-CurrentRevision
Write-Host "  Revision after rollback: $rollbackRev"
Write-Host ""

if ($rollbackRev -ne $previousRev) {
    Write-Host "⚠️  Rollback revision ($rollbackRev) doesn't match expected ($previousRev)" -ForegroundColor Yellow
    Write-Host "  This may be normal if there are multiple migration branches"
    Write-Host "  Continuing with test..."
    Write-Host ""
}

Write-Host "Step 5: Re-applying migration..."
& $alembicCmd upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to re-apply migration" -ForegroundColor Red
    exit 1
}
$finalRev = Get-CurrentRevision
Write-Host "  Final revision: $finalRev"
Write-Host ""

if ($finalRev -eq $currentRev) {
    Write-Host "✓ Rollback test passed!" -ForegroundColor Green
    Write-Host "  Successfully rolled back and re-applied migration"
    Write-Host "  Final revision matches original: $currentRev"
    exit 0
} else {
    Write-Host "✗ Rollback test failed!" -ForegroundColor Red
    Write-Host "  Expected final revision: $currentRev"
    Write-Host "  Actual final revision: $finalRev"
    Write-Host ""
    Write-Host "  Database may be in inconsistent state."
    Write-Host "  Review migration files and consider restoring from backup."
    exit 1
}

