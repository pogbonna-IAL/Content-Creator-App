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

# Validate DATABASE_URL format before creating engine
def validate_database_url(url: str) -> None:
    """Validate DATABASE_URL format and provide helpful error messages"""
    import re
    from urllib.parse import urlparse
    
    # Check for common malformed patterns
    if "://" not in url:
        logger.error("=" * 60)
        logger.error("❌ MALFORMED DATABASE_URL")
        logger.error("=" * 60)
        logger.error("DATABASE_URL must include '://' protocol separator")
        logger.error(f"Got: {url[:100]}...")
        logger.error("Expected format: postgresql://user:password@host:port/database")
        logger.error("=" * 60)
        sys.exit(1)
    
    # Parse URL to check components
    try:
        parsed = urlparse(url)
        
        # Check for empty port (host: without port number)
        if parsed.hostname and ":" in parsed.netloc and not parsed.port:
            # Check if there's a trailing colon without port
            netloc_parts = parsed.netloc.split("@")
            if len(netloc_parts) > 1:
                host_part = netloc_parts[-1]
                if host_part.count(":") > 0 and not any(c.isdigit() for c in host_part.split(":")[-1]):
                    logger.error("=" * 60)
                    logger.error("❌ MALFORMED DATABASE_URL - EMPTY PORT")
                    logger.error("=" * 60)
                    logger.error("DATABASE_URL has an empty port number (trailing colon without port)")
                    logger.error(f"Got: {url[:100]}...")
                    logger.error("")
                    logger.error("Common causes:")
                    logger.error("1. DATABASE_URL has format: postgresql://user:pass@host:/database")
                    logger.error("2. Railway variable DATABASE_URL is incorrectly set")
                    logger.error("3. Missing port number in connection string")
                    logger.error("")
                    logger.error("Expected format: postgresql://user:password@host:5432/database")
                    logger.error("")
                    logger.error("SOLUTION:")
                    logger.error("1. Go to Railway Dashboard → Backend Service → Variables")
                    logger.error("2. Check DATABASE_URL value")
                    logger.error("3. Ensure it includes port number (usually :5432)")
                    logger.error("4. If incorrect, delete it and re-link PostgreSQL service")
                    logger.error("=" * 60)
                    sys.exit(1)
    except Exception as e:
        # If parsing fails, we'll let SQLAlchemy handle it with better error
        pass

# Validate DATABASE_URL format
validate_database_url(config.DATABASE_URL)

# Create PostgreSQL engine with production-ready pool settings
try:
    engine = create_engine(
        config.DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using (health check)
        pool_size=config.DB_POOL_SIZE,  # Base pool size (default: 10)
        max_overflow=config.DB_MAX_OVERFLOW,  # Additional connections (default: 10, total: 20)
        pool_recycle=config.DB_POOL_RECYCLE,  # Recycle connections after 1 hour (default)
        pool_timeout=config.DB_POOL_TIMEOUT,  # Wait up to 30s for connection (default)
        echo=False,  # Disable SQL logging for performance
        connect_args={
            "connect_timeout": 5,  # Connection timeout (5 seconds)
            "keepalives": 1,  # Enable TCP keepalives
            "keepalives_idle": 30,  # Start keepalives after 30 seconds idle
            "keepalives_interval": 10,  # Send keepalive every 10 seconds
            "keepalives_count": 3,  # Keepalive failures before disconnect
            "application_name": "content_creation_crew",
            # Set statement timeout at connection level (default: 10 seconds)
            "options": f"-c statement_timeout={config.DB_STATEMENT_TIMEOUT}",
        }
    )
except ValueError as e:
    # Catch SQLAlchemy URL parsing errors (e.g., empty port)
    error_str = str(e).lower()
    if "invalid literal for int()" in error_str or "port" in error_str:
        logger.error("=" * 60)
        logger.error("❌ MALFORMED DATABASE_URL - URL PARSING ERROR")
        logger.error("=" * 60)
        logger.error(f"SQLAlchemy could not parse DATABASE_URL: {e}")
        logger.error(f"DATABASE_URL: {config.DATABASE_URL[:100]}...")
        logger.error("")
        logger.error("Common causes:")
        logger.error("1. Empty port number (host: without port)")
        logger.error("2. Invalid port format")
        logger.error("3. Malformed connection string")
        logger.error("")
        logger.error("Expected format: postgresql://user:password@host:5432/database")
        logger.error("")
        logger.error("SOLUTION:")
        logger.error("1. Go to Railway Dashboard → Backend Service → Variables")
        logger.error("2. Check DATABASE_URL value")
        logger.error("3. Ensure format is: postgresql://user:password@host:PORT/database")
        logger.error("4. If incorrect, delete it and re-link PostgreSQL service")
        logger.error("5. Railway will automatically set correct DATABASE_URL when services are linked")
        logger.error("=" * 60)
    else:
        logger.error(f"Error creating database engine: {e}")
    sys.exit(1)
except Exception as e:
    logger.error("=" * 60)
    logger.error("❌ ERROR CREATING DATABASE ENGINE")
    logger.error("=" * 60)
    logger.error(f"Unexpected error: {e}")
    logger.error(f"DATABASE_URL: {config.DATABASE_URL[:100]}...")
    logger.error("=" * 60)
    sys.exit(1)

logger.info(f"PostgreSQL engine configured:")
logger.info(f"  - Pool size: {config.DB_POOL_SIZE}")
logger.info(f"  - Max overflow: {config.DB_MAX_OVERFLOW}")
logger.info(f"  - Total max connections: {config.DB_POOL_SIZE + config.DB_MAX_OVERFLOW}")
logger.info(f"  - Pool timeout: {config.DB_POOL_TIMEOUT}s")
logger.info(f"  - Statement timeout: {config.DB_STATEMENT_TIMEOUT}ms")

# Add event listeners for connection pool management
@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Called when a connection is retrieved from the pool"""
    # Track pool statistics
    pool_status = engine.pool.status()
    logger.debug(f"Connection checked out from pool | Pool status: {pool_status}")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Called when a connection is returned to the pool"""
    logger.debug("Connection checked in to pool")

@event.listens_for(Pool, "invalidate")
def receive_invalidate(dbapi_conn, connection_record, exception):
    """Called when a connection is invalidated"""
    logger.warning(f"Connection invalidated: {exception}")

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Called when a new connection is created"""
    logger.debug("New database connection created")

@event.listens_for(Pool, "close")
def receive_close(dbapi_conn, connection_record):
    """Called when a connection is closed"""
    logger.debug("Database connection closed")

logger.info("✓ PostgreSQL engine created successfully")

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

