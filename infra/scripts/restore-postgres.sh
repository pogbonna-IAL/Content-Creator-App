#!/bin/bash
# PostgreSQL Restore Script
# Restores a PostgreSQL database from a backup file

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "PostgreSQL Restore Script"
echo "=========================================="
echo ""

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}✗ Backup file is required${NC}"
    echo ""
    echo "Usage:"
    echo "  bash infra/scripts/restore-postgres.sh <backup_file.dump>"
    echo "  or"
    echo "  make restore-db <backup_file.dump>"
    echo ""
    echo "Example:"
    echo "  bash infra/scripts/restore-postgres.sh ./backups/postgres/content_crew_20260113_020000.dump"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}✗ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Check if backup file is encrypted
ENCRYPTED=false
DECRYPTED_FILE="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.enc ]]; then
    ENCRYPTED=true
    DECRYPTED_FILE="${BACKUP_FILE%.enc}"
    
    if [ -z "$BACKUP_ENCRYPTION_KEY" ]; then
        echo -e "${RED}✗ Encrypted backup requires BACKUP_ENCRYPTION_KEY environment variable${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}Decrypting backup file...${NC}"
    if command -v openssl &> /dev/null; then
        openssl enc -aes-256-cbc -d -in "$BACKUP_FILE" -out "$DECRYPTED_FILE" -k "$BACKUP_ENCRYPTION_KEY"
        echo -e "${GREEN}✓ Backup decrypted${NC}"
    else
        echo -e "${RED}✗ openssl not found, cannot decrypt backup${NC}"
        exit 1
    fi
fi

BACKUP_FILE="$DECRYPTED_FILE"

# Detect database connection method
if docker compose ps db 2>/dev/null | grep -q "Up"; then
    echo -e "${BLUE}Detected Docker Compose PostgreSQL${NC}"
    DB_METHOD="docker"
    
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
    
    # Extract database name from URL
    DB_NAME=$(echo "$DB_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
elif command -v psql &> /dev/null; then
    echo -e "${BLUE}Using local PostgreSQL connection${NC}"
    DB_METHOD="local"
    DB_HOST="${PGHOST:-localhost}"
    DB_PORT="${PGPORT:-5432}"
    DB_USER="${PGUSER:-postgres}"
    DB_NAME="${PGDATABASE:-content_crew}"
else
    echo -e "${RED}✗ Cannot find PostgreSQL connection${NC}"
    exit 1
fi

echo ""
echo "⚠️  WARNING: This will overwrite the existing database!"
echo "  Backup file: $BACKUP_FILE"
echo "  Target database: $DB_NAME"
echo ""

# Confirmation prompt
read -p "Are you sure you want to proceed? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    # Clean up decrypted file if it was encrypted
    if [ "$ENCRYPTED" = true ] && [ -f "$DECRYPTED_FILE" ]; then
        rm "$DECRYPTED_FILE"
    fi
    exit 0
fi

# Stop application (if running)
echo ""
echo -e "${BLUE}Stopping application...${NC}"
if docker compose ps api 2>/dev/null | grep -q "Up"; then
    docker compose stop api
    echo -e "${GREEN}✓ Application stopped${NC}"
fi

# Verify backup file
echo ""
echo -e "${BLUE}Verifying backup file...${NC}"
if [ "$DB_METHOD" = "docker" ]; then
    if docker compose exec -T "$DB_CONTAINER" pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backup file is valid${NC}"
    else
        echo -e "${RED}✗ Backup file appears to be invalid${NC}"
        exit 1
    fi
else
    if pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backup file is valid${NC}"
    else
        echo -e "${RED}✗ Backup file appears to be invalid${NC}"
        exit 1
    fi
fi

# Perform restore
echo ""
echo -e "${BLUE}Starting restore...${NC}"

if [ "$DB_METHOD" = "docker" ]; then
    # Docker restore
    echo "Restoring to Docker container..."
    
    # Drop existing connections
    docker compose exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
    " || true
    
    # Drop and recreate database
    echo "Dropping existing database..."
    docker compose exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
    
    echo "Creating new database..."
    docker compose exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
    
    echo "Restoring data..."
    if docker compose exec -T "$DB_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl < "$BACKUP_FILE"; then
        RESTORE_SUCCESS=true
    else
        RESTORE_SUCCESS=false
    fi
elif [ "$DB_METHOD" = "url" ]; then
    # DATABASE_URL restore
    echo "Restoring from DATABASE_URL..."
    
    # Extract base URL (without database name)
    BASE_URL=$(echo "$DB_URL" | sed 's|/[^/]*$||')
    
    # Drop and recreate database
    echo "Dropping existing database..."
    psql "$BASE_URL/postgres" -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
    
    echo "Creating new database..."
    psql "$BASE_URL/postgres" -c "CREATE DATABASE $DB_NAME;"
    
    echo "Restoring data..."
    if pg_restore -d "$DB_URL" --no-owner --no-acl "$BACKUP_FILE"; then
        RESTORE_SUCCESS=true
    else
        RESTORE_SUCCESS=false
    fi
else
    # Local restore
    echo "Restoring to local PostgreSQL..."
    
    export PGHOST="$DB_HOST"
    export PGPORT="$DB_PORT"
    export PGUSER="$DB_USER"
    
    # Drop and recreate database
    echo "Dropping existing database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
    
    echo "Creating new database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
    
    echo "Restoring data..."
    if pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl "$BACKUP_FILE"; then
        RESTORE_SUCCESS=true
    else
        RESTORE_SUCCESS=false
    fi
fi

# Clean up decrypted file if it was encrypted
if [ "$ENCRYPTED" = true ] && [ -f "$DECRYPTED_FILE" ]; then
    rm "$DECRYPTED_FILE"
fi

if [ "$RESTORE_SUCCESS" = true ]; then
    echo ""
    echo -e "${GREEN}✓ Restore completed successfully${NC}"
    
    # Verify restore
    echo ""
    echo -e "${BLUE}Verifying restore...${NC}"
    
    if [ "$DB_METHOD" = "docker" ]; then
        TABLE_COUNT=$(docker compose exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
        USER_COUNT=$(docker compose exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    else
        TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
        USER_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM users;" | tr -d ' ')
    fi
    
    echo "  Tables restored: $TABLE_COUNT"
    echo "  Users in database: $USER_COUNT"
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}Restore Summary${NC}"
    echo "=========================================="
    echo "  Database: $DB_NAME"
    echo "  Tables: $TABLE_COUNT"
    echo "  Users: $USER_COUNT"
    echo ""
    echo "Next steps:"
    echo "  1. Restart application: docker compose start api"
    echo "  2. Verify health: curl http://localhost:8000/health"
    echo "  3. Test functionality: Create a test content job"
    
    exit 0
else
    echo ""
    echo -e "${RED}✗ Restore failed${NC}"
    echo ""
    echo "Check:"
    echo "  1. Database is running and accessible"
    echo "  2. Database credentials are correct"
    echo "  3. Backup file is valid"
    echo "  4. Sufficient disk space available"
    exit 1
fi

