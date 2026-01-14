#!/bin/bash
# Create database backup (M2)
# Usage: ./create-backup.sh [output_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${1:-${BACKUP_DIR}/backup_${TIMESTAMP}.sql}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "DATABASE BACKUP"
echo "=========================================="

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Get database connection details from environment
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-content_creation_crew}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

echo "Database: ${DB_NAME}"
echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Output: ${OUTPUT_FILE}"
echo ""

# Export password for pg_dump
if [ -n "$DB_PASSWORD" ]; then
    export PGPASSWORD="$DB_PASSWORD"
fi

# Create backup
echo "Creating backup..."
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    -f "$OUTPUT_FILE"

# Check if backup was created
if [ -f "$OUTPUT_FILE" ]; then
    SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
    echo ""
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  File: ${OUTPUT_FILE}"
    echo "  Size: ${SIZE} bytes"
    echo ""
    
    # Compress backup
    echo "Compressing backup..."
    gzip -f "$OUTPUT_FILE"
    COMPRESSED_FILE="${OUTPUT_FILE}.gz"
    COMPRESSED_SIZE=$(stat -f%z "$COMPRESSED_FILE" 2>/dev/null || stat -c%s "$COMPRESSED_FILE" 2>/dev/null)
    
    echo -e "${GREEN}✓ Backup compressed${NC}"
    echo "  File: ${COMPRESSED_FILE}"
    echo "  Size: ${COMPRESSED_SIZE} bytes"
    echo "  Compression: $(awk "BEGIN {printf \"%.1f%%\", (1-${COMPRESSED_SIZE}/${SIZE})*100}")"
    
    exit 0
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

