"""
Database module - Backward compatibility wrapper
This module provides backward compatibility while transitioning to the new db/ structure.
All code should eventually migrate to use content_creation_crew.db directly.
"""
import logging
import sys
from typing import Generator

# Import from new db module
from .db import (
    engine,
    SessionLocal,
    get_db,
    Base,
    User,
    Session,
    Organization,
    Membership,
    Subscription,
    UsageCounter,
    ContentJob,
    ContentArtifact,
    BillingEvent,
)
# Import enums for convenience
from .db.models.organization import MembershipRole
from .db.models.subscription import SubscriptionPlan, SubscriptionStatus, PaymentProvider
from .db.models.content import JobStatus, ContentType
from .db.models.billing import BillingEventType
from .db.engine import test_connection

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
    "User",
    "Session",
    "Organization",
    "Membership",
    "Subscription",
    "UsageCounter",
    "ContentJob",
    "ContentArtifact",
    "BillingEvent",
    "MembershipRole",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "PaymentProvider",
    "JobStatus",
    "ContentType",
    "BillingEventType",
    "init_db",
    "test_connection",
]

# Backward compatibility: DATABASE_URL (deprecated - use config.DATABASE_URL)
def _get_database_url():
    """Get database URL from config (backward compatibility)"""
    from .config import config
    return config.DATABASE_URL

DATABASE_URL = _get_database_url()


def init_db():
    """
    Initialize database tables using Alembic migrations.
    This is called at application startup.
    """
    import sys
    import time
    
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("🔄 Database Migration Process Starting")
    logger.info("=" * 60)
    
    # Test database connection first
    logger.info("Step 1/3: Testing database connection...")
    print("[MIGRATION] Step 1/3: Testing database connection...", file=sys.stdout, flush=True)
    if not test_connection():
        logger.warning("Database connection test failed - will retry on first request")
        logger.warning("Application will continue but database features may not work until connection is established")
        print("[MIGRATION] WARNING: Database connection test failed", file=sys.stdout, flush=True)
        return
    
    connection_time = time.time() - start_time
    logger.info(f"✓ Database connection successful ({connection_time:.2f}s)")
    print(f"[MIGRATION] ✓ Database connection successful ({connection_time:.2f}s)", file=sys.stdout, flush=True)
    
    try:
        # Run migrations using Alembic
        logger.info("Step 2/3: Loading Alembic configuration...")
        print("[MIGRATION] Step 2/3: Loading Alembic configuration...", file=sys.stdout, flush=True)
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        logger.info("Step 3/3: Running migrations (alembic upgrade head)...")
        print("[MIGRATION] Step 3/3: Running migrations (alembic upgrade head)...", file=sys.stdout, flush=True)
        
        migration_start = time.time()
        command.upgrade(alembic_cfg, "head")
        migration_duration = time.time() - migration_start
        total_duration = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info(f"✅ Database migrations completed successfully")
        logger.info(f"   Migration time: {migration_duration:.2f}s")
        logger.info(f"   Total time: {total_duration:.2f}s")
        logger.info("=" * 60)
        print(f"[MIGRATION] ✅ Database migrations completed successfully ({migration_duration:.2f}s)", file=sys.stdout, flush=True)
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error("=" * 60)
        logger.error(f"❌ Migration failed after {total_duration:.2f}s: {e}", exc_info=True)
        logger.error("Application will continue but database features may not work until migrations are applied")
        logger.error("Run 'make migrate' or 'alembic upgrade head' to apply migrations")
        logger.error("=" * 60)
        print(f"[MIGRATION] ❌ Migration failed after {total_duration:.2f}s: {e}", file=sys.stdout, flush=True)
        raise