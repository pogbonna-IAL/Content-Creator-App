#!/usr/bin/env python
"""
Database migration script
Run this to apply database migrations
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alembic.config import Config
from alembic import command

def upgrade_db():
    """Upgrade database to latest migration"""
    alembic_cfg = Config("alembic.ini")
    print("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("✓ Database migrations completed successfully!")

def downgrade_db(revision: str = "-1"):
    """Downgrade database by one revision (or to specific revision)"""
    alembic_cfg = Config("alembic.ini")
    print(f"Downgrading database to revision: {revision}")
    command.downgrade(alembic_cfg, revision)
    print("✓ Database downgrade completed!")

def show_current_revision():
    """Show current database revision"""
    alembic_cfg = Config("alembic.ini")
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from content_creation_crew.database import engine
    
    script = ScriptDirectory.from_config(alembic_cfg)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        if current_rev:
            print(f"Current database revision: {current_rev}")
        else:
            print("Database is not initialized. Run migrations first.")
        
        head_rev = script.get_current_head()
        print(f"Latest migration available: {head_rev}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "downgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
            downgrade_db(revision)
        elif sys.argv[1] == "current":
            show_current_revision()
        elif sys.argv[1] == "upgrade":
            upgrade_db()
        else:
            print("Usage: python migrate_db.py [upgrade|downgrade [revision]|current]")
    else:
        upgrade_db()

