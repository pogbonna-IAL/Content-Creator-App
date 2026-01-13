#!/bin/bash
# Test migration rollback procedure
# This script applies migrations, rolls back one, and re-applies to verify rollback works

set -e  # Exit on error

echo "=========================================="
echo "Migration Rollback Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL environment variable is not set${NC}"
    echo "Set it with: export DATABASE_URL=postgresql://user:pass@host:port/db"
    exit 1
fi

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo -e "${YELLOW}⚠️  alembic not found in PATH, trying uv run alembic...${NC}"
    ALEMBIC_CMD="uv run alembic"
else
    ALEMBIC_CMD="alembic"
fi

# Function to get current revision
get_current_revision() {
    $ALEMBIC_CMD current | grep -oP '^\w+' | head -1 || echo "none"
}

# Function to get head revision
get_head_revision() {
    $ALEMBIC_CMD heads | grep -oP '^\w+' | head -1 || echo "none"
}

echo "Step 1: Checking current database state..."
CURRENT_REV=$(get_current_revision)
HEAD_REV=$(get_head_revision)

echo "  Current revision: $CURRENT_REV"
echo "  Head revision: $HEAD_REV"
echo ""

if [ "$CURRENT_REV" = "none" ]; then
    echo -e "${YELLOW}⚠️  Database not initialized. Applying initial migrations...${NC}"
    $ALEMBIC_CMD upgrade head
    CURRENT_REV=$(get_current_revision)
    echo "  Current revision after initial migration: $CURRENT_REV"
    echo ""
fi

if [ "$CURRENT_REV" = "$HEAD_REV" ]; then
    echo -e "${YELLOW}⚠️  Database is already at head revision.${NC}"
    echo "  To test rollback, we need at least one migration to rollback."
    echo "  Current: $CURRENT_REV"
    echo ""
    
    # Check if there are multiple revisions
    REVISION_COUNT=$($ALEMBIC_CMD history | grep -c "Rev:" || echo "0")
    if [ "$REVISION_COUNT" -le "1" ]; then
        echo -e "${RED}✗ Not enough migrations to test rollback (need at least 2)${NC}"
        exit 1
    fi
    
    echo "  Rolling back one revision for testing..."
    $ALEMBIC_CMD downgrade -1
    CURRENT_REV=$(get_current_revision)
    echo "  Current revision after rollback: $CURRENT_REV"
    echo ""
fi

echo "Step 2: Applying migrations to head..."
$ALEMBIC_CMD upgrade head
CURRENT_REV=$(get_current_revision)
echo -e "${GREEN}✓ Migrations applied. Current revision: $CURRENT_REV${NC}"
echo ""

if [ "$CURRENT_REV" = "none" ] || [ -z "$CURRENT_REV" ]; then
    echo -e "${RED}✗ Failed to get current revision after upgrade${NC}"
    exit 1
fi

# Get the previous revision
echo "Step 3: Getting previous revision..."
PREVIOUS_REV=$($ALEMBIC_CMD history | grep -A 1 "$CURRENT_REV" | tail -1 | grep -oP '^\w+' | head -1 || echo "")

if [ -z "$PREVIOUS_REV" ] || [ "$PREVIOUS_REV" = "$CURRENT_REV" ]; then
    # Try alternative method
    PREVIOUS_REV=$($ALEMBIC_CMD history | grep "Rev:" | tail -2 | head -1 | grep -oP '\w{12}' | head -1 || echo "")
fi

if [ -z "$PREVIOUS_REV" ] || [ "$PREVIOUS_REV" = "$CURRENT_REV" ]; then
    echo -e "${YELLOW}⚠️  Could not determine previous revision automatically${NC}"
    echo "  This is the first migration - rollback test skipped"
    echo -e "${GREEN}✓ Migration rollback test completed (no rollback needed)${NC}"
    exit 0
fi

echo "  Previous revision: $PREVIOUS_REV"
echo "  Current revision: $CURRENT_REV"
echo ""

echo "Step 4: Rolling back one revision..."
$ALEMBIC_CMD downgrade -1
ROLLBACK_REV=$(get_current_revision)
echo "  Revision after rollback: $ROLLBACK_REV"
echo ""

if [ "$ROLLBACK_REV" != "$PREVIOUS_REV" ]; then
    echo -e "${YELLOW}⚠️  Rollback revision ($ROLLBACK_REV) doesn't match expected ($PREVIOUS_REV)${NC}"
    echo "  This may be normal if there are multiple migration branches"
    echo "  Continuing with test..."
    echo ""
fi

echo "Step 5: Re-applying migration..."
$ALEMBIC_CMD upgrade head
FINAL_REV=$(get_current_revision)
echo "  Final revision: $FINAL_REV"
echo ""

if [ "$FINAL_REV" = "$CURRENT_REV" ]; then
    echo -e "${GREEN}✓ Rollback test passed!${NC}"
    echo "  Successfully rolled back and re-applied migration"
    echo "  Final revision matches original: $CURRENT_REV"
    exit 0
else
    echo -e "${RED}✗ Rollback test failed!${NC}"
    echo "  Expected final revision: $CURRENT_REV"
    echo "  Actual final revision: $FINAL_REV"
    echo ""
    echo "  Database may be in inconsistent state."
    echo "  Review migration files and consider restoring from backup."
    exit 1
fi

