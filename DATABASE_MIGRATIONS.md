# Database Migrations Guide

This project uses **Alembic** for database migrations (the Python equivalent of Prisma migrations for Node.js).

## Why Alembic instead of Prisma?

- **Prisma** is a Node.js/TypeScript ORM that doesn't work with Python
- **Alembic** is the standard migration tool for SQLAlchemy (Python)
- Our backend is Python/FastAPI, so we use Alembic for migrations

## Database Schema

The authentication system uses two main tables:

1. **users** - Stores user accounts (email/password and OAuth)
2. **sessions** - Stores user sessions (currently not used, reserved for future token blacklisting)

## Running Migrations

### Initial Setup

On first run, the database will be automatically migrated when the API server starts.

### Manual Migration Commands

```bash
# Upgrade to latest migration
uv run alembic upgrade head

# Or use the migration script
python migrate_db.py

# Show current revision
python migrate_db.py current

# Downgrade by one revision
python migrate_db.py downgrade

# Downgrade to specific revision
python migrate_db.py downgrade <revision_id>
```

### Creating New Migrations

When you modify the database models in `src/content_creation_crew/database.py`:

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file in alembic/versions/

# Apply the migration
uv run alembic upgrade head
```

## Migration Files

- Migration files are stored in `alembic/versions/`
- Each migration has a unique revision ID
- Migrations are applied in order

## Current Schema

### Users Table
- `id` (Integer, Primary Key)
- `email` (String, Unique, Indexed)
- `hashed_password` (String, Nullable - for OAuth users)
- `full_name` (String, Nullable)
- `is_active` (Boolean, Default: True)
- `is_verified` (Boolean, Default: False)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `provider` (String, Nullable - 'google', 'facebook', 'github', 'email')
- `provider_id` (String, Nullable - OAuth provider user ID)

### Sessions Table
- `id` (Integer, Primary Key)
- `user_id` (Integer, Foreign Key to users.id)
- `token` (String, Unique, Indexed)
- `expires_at` (DateTime)
- `created_at` (DateTime)

## Troubleshooting

### Database Locked Error
If you get a "database is locked" error:
1. Make sure no other process is using the database
2. Close any database viewers/editors
3. Restart the API server

### Migration Conflicts
If migrations fail:
1. Check the error message
2. Review the migration file in `alembic/versions/`
3. You may need to manually edit the migration or rollback

### Reset Database
To completely reset the database:
```bash
# Delete the database file
rm content_crew.db

# Run migrations to recreate
uv run alembic upgrade head
```

## Production Considerations

For production, consider:
1. Using PostgreSQL instead of SQLite
2. Setting up automated backups
3. Using environment variables for database URL
4. Setting up migration CI/CD pipeline

To switch to PostgreSQL:
1. Update `DATABASE_URL` in `database.py`
2. Install PostgreSQL driver: `psycopg2` or `asyncpg`
3. Update `alembic.ini` with PostgreSQL connection string

