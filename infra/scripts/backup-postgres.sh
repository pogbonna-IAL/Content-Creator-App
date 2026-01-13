#!/bin/bash
# PostgreSQL Backup Script
# Creates a compressed backup of the PostgreSQL database

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "PostgreSQL Backup Script"
echo "=========================================="
echo ""

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${1:-${BACKUP_DIR}/content_crew_${TIMESTAMP}.dump}"

# Create backup directory if it doesn't exist
mkdir -p "$(dirname "$BACKUP_FILE")"

# Detect database connection method
if docker compose ps db 2>/dev/null | grep -q "Up"; then
    echo -e "${BLUE}Detected Docker Compose PostgreSQL${NC}"
    DB_METHOD="docker"
    
    # Get database credentials from docker-compose
    DB_USER="${POSTGRES_USER:-contentcrew}"
    DB_NAME="${POSTGRES_DB:-content_crew}"
    DB_CONTAINER="content-crew-db"
    
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Container: $DB_CONTAINER"
elif [ -n "$DATABASE_URL" ]; then
    echo -e "${BLUE}Using DATABASE_URL environment variable${NC}"
    DB_METHOD="url"
    DB_URL="$DATABASE_URL"
elif command -v psql &> /dev/null; then
    echo -e "${BLUE}Using local PostgreSQL connection${NC}"
    DB_METHOD="local"
    DB_HOST="${PGHOST:-localhost}"
    DB_PORT="${PGPORT:-5432}"
    DB_USER="${PGUSER:-postgres}"
    DB_NAME="${PGDATABASE:-content_crew}"
else
    echo -e "${RED}✗ Cannot find PostgreSQL connection${NC}"
    echo ""
    echo "Options:"
    echo "  1. Start Docker Compose: docker compose up -d db"
    echo "  2. Set DATABASE_URL environment variable"
    echo "  3. Install PostgreSQL client and configure connection"
    exit 1
fi

echo ""
echo "Backup file: $BACKUP_FILE"
echo ""

# Perform backup
echo -e "${BLUE}Starting backup...${NC}"

if [ "$DB_METHOD" = "docker" ]; then
    # Docker backup
    echo "Creating backup from Docker container..."
    if docker compose exec -T "$DB_CONTAINER" pg_dump -U "$DB_USER" -Fc "$DB_NAME" > "$BACKUP_FILE"; then
        BACKUP_SUCCESS=true
    else
        BACKUP_SUCCESS=false
    fi
elif [ "$DB_METHOD" = "url" ]; then
    # DATABASE_URL backup
    echo "Creating backup from DATABASE_URL..."
    if pg_dump -Fc "$DB_URL" -f "$BACKUP_FILE"; then
        BACKUP_SUCCESS=true
    else
        BACKUP_SUCCESS=false
    fi
else
    # Local backup
    echo "Creating backup from local PostgreSQL..."
    export PGHOST="$DB_HOST"
    export PGPORT="$DB_PORT"
    export PGUSER="$DB_USER"
    export PGDATABASE="$DB_NAME"
    
    if pg_dump -Fc -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE"; then
        BACKUP_SUCCESS=true
    else
        BACKUP_SUCCESS=false
    fi
fi

if [ "$BACKUP_SUCCESS" = true ]; then
    # Check backup file
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}✗ Backup file was not created${NC}"
        exit 1
    fi
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    
    # Verify backup integrity
    echo ""
    echo -e "${BLUE}Verifying backup integrity...${NC}"
    
    if [ "$DB_METHOD" = "docker" ]; then
        if docker compose exec -T "$DB_CONTAINER" pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backup integrity verified${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not verify backup integrity (may still be valid)${NC}"
        fi
    else
        if pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backup integrity verified${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not verify backup integrity (may still be valid)${NC}"
        fi
    fi
    
    # Optional encryption
    if [ -n "$BACKUP_ENCRYPTION_KEY" ]; then
        echo ""
        echo -e "${BLUE}Encrypting backup...${NC}"
        ENCRYPTED_FILE="${BACKUP_FILE}.enc"
        
        if command -v openssl &> /dev/null; then
            openssl enc -aes-256-cbc -salt -in "$BACKUP_FILE" -out "$ENCRYPTED_FILE" -k "$BACKUP_ENCRYPTION_KEY"
            rm "$BACKUP_FILE"
            echo -e "${GREEN}✓ Backup encrypted: $ENCRYPTED_FILE${NC}"
            BACKUP_FILE="$ENCRYPTED_FILE"
        else
            echo -e "${YELLOW}⚠️  openssl not found, skipping encryption${NC}"
        fi
    fi
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}Backup Summary${NC}"
    echo "=========================================="
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo "  Timestamp: $TIMESTAMP"
    echo ""
    echo "To restore this backup:"
    echo "  make restore-db $BACKUP_FILE"
    echo "  or"
    echo "  bash infra/scripts/restore-postgres.sh $BACKUP_FILE"
    
    exit 0
else
    echo -e "${RED}✗ Backup failed${NC}"
    echo ""
    echo "Check:"
    echo "  1. Database is running and accessible"
    echo "  2. Database credentials are correct"
    echo "  3. Sufficient disk space available"
    echo "  4. Backup directory is writable"
    exit 1
fi

