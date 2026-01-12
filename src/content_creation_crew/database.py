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
    # Test database connection first
    if not test_connection():
        logger.warning("Database connection test failed - will retry on first request")
        logger.warning("Application will continue but database features may not work until connection is established")
        return
    
    try:
        # Run migrations using Alembic
        from alembic.config import Config
        from alembic import command
        
        logger.info("Running database migrations...")
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✓ Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        logger.error("Application will continue but database features may not work until migrations are applied")
        logger.error("Run 'make migrate' or 'alembic upgrade head' to apply migrations")
