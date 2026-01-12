"""
Database engine and session management
PostgreSQL-only implementation
"""
import logging
import sys
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from typing import Generator

from ..config import config

logger = logging.getLogger(__name__)

# Validate DATABASE_URL is PostgreSQL
if not config.DATABASE_URL:
    logger.error("=" * 60)
    logger.error("❌ DATABASE_URL NOT SET")
    logger.error("=" * 60)
    logger.error("DATABASE_URL environment variable is required.")
    logger.error("It must be a PostgreSQL connection string.")
    logger.error("Example: postgresql://user:password@localhost:5432/dbname")
    logger.error("=" * 60)
    sys.exit(1)

if not config.DATABASE_URL.startswith("postgresql"):
    logger.error("=" * 60)
    logger.error("❌ INVALID DATABASE_URL")
    logger.error("=" * 60)
    logger.error(f"DATABASE_URL must be a PostgreSQL connection string.")
    logger.error(f"Got: {config.DATABASE_URL[:50]}...")
    logger.error("SQLite is no longer supported.")
    logger.error("=" * 60)
    sys.exit(1)

# Create PostgreSQL engine with optimized pool settings
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=2,  # Minimal pool size
    max_overflow=3,  # Minimal overflow
    pool_recycle=900,  # Recycle connections after 15 minutes
    pool_timeout=10,  # Reduced timeout to fail faster
    echo=False,  # Disable SQL logging for performance
    connect_args={
        "connect_timeout": 3,  # Very short connection timeout
        "keepalives": 1,  # Enable TCP keepalives
        "keepalives_idle": 30,  # Start keepalives after 30 seconds idle
        "keepalives_interval": 10,  # Send keepalive every 10 seconds
        "keepalives_count": 3,  # Reduced keepalive failures before disconnect
        "application_name": "content_creation_crew",
    }
)

# Add event listeners for connection pool management
@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Called when a connection is retrieved from the pool"""
    logger.debug("Connection checked out from pool")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Called when a connection is returned to the pool"""
    logger.debug("Connection checked in to pool")

@event.listens_for(Pool, "invalidate")
def receive_invalidate(dbapi_conn, connection_record, exception):
    """Called when a connection is invalidated"""
    logger.warning(f"Connection invalidated: {exception}")

logger.info("PostgreSQL engine created successfully")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    Get database session with proper error handling and connection management.
    Use as FastAPI dependency: db: Session = Depends(get_db)
    """
    db = None
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    # Retry loop for getting connection from pool
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            break  # Successfully got connection
        except Exception as e:
            # Check if it's a pool-related error
            error_str = str(e).lower()
            is_pool_error = any(keyword in error_str for keyword in [
                'pool', 'connection', 'timeout', 'checkout', '_do_get', 
                'could not get connection', '_connectionrecord', 'checkout(pool)'
            ])
            
            if attempt < max_retries - 1 and is_pool_error:
                # Pool error, retry after short delay
                logger.warning(
                    f"Database pool error getting connection (attempt {attempt + 1}/{max_retries}): {e}. Retrying..."
                )
                import time
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                # Not a pool error or max retries reached
                if is_pool_error:
                    logger.error("=" * 60)
                    logger.error("❌ DATABASE POOL CHECKOUT ERROR")
                    logger.error("=" * 60)
                    logger.error(f"Failed to checkout connection from pool: {e}")
                    logger.error("")
                    logger.error("POSSIBLE CAUSES:")
                    logger.error("1. Connection pool exhausted (all connections in use)")
                    logger.error("2. Database connectivity issues")
                    logger.error("3. DATABASE_URL incorrect")
                    logger.error("4. PostgreSQL service not properly linked")
                    logger.error("=" * 60)
                logger.error(f"Failed to get database connection: {e}", exc_info=True)
                raise
    
    # Yield the session (FastAPI dependency pattern)
    try:
        yield db
        db.commit()
    except Exception as e:
        if db:
            try:
                db.rollback()
            except Exception:
                pass  # Ignore rollback errors
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")


def test_connection() -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection test failed: {e}", exc_info=True)
        return False

