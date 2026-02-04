"""
Database engine and session management
PostgreSQL-only implementation
"""
import logging
import sys
import threading
import time
import psycopg2
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import Pool
from sqlalchemy.exc import OperationalError, DisconnectionError
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
        pool_pre_ping=True,  # Verify connections before using (health check) - CRITICAL for detecting dead connections
        pool_size=config.DB_POOL_SIZE,  # Base pool size (default: 20)
        max_overflow=config.DB_MAX_OVERFLOW,  # Additional connections (default: 10, total: 30)
        pool_recycle=config.DB_POOL_RECYCLE,  # Recycle connections after 15 minutes (900s) - prevents stale SSL connections
        pool_timeout=config.DB_POOL_TIMEOUT,  # Wait up to 30s for connection (default)
        echo=False,  # Disable SQL logging for performance
        connect_args={
            "connect_timeout": 10,  # Connection timeout (increased to 10 seconds for reliability)
            "keepalives": 1,  # Enable TCP keepalives
            "keepalives_idle": 60,  # Start keepalives after 60 seconds idle (less aggressive)
            "keepalives_interval": 10,  # Send keepalive every 10 seconds
            "keepalives_count": 3,  # Keepalive failures before disconnect (reduced for faster reconnection)
            "application_name": "content_creation_crew",
            # Explicit SSL mode configuration - require SSL but allow self-signed certs
            "sslmode": "require",  # Force SSL, but allow self-signed certs (Railway uses valid certs)
            # Set statement timeout and idle transaction timeout at connection level
            # Note: DB_STATEMENT_TIMEOUT is in milliseconds, so 10000 = 10 seconds
            # idle_in_transaction_session_timeout prevents transactions from staying open too long (20 seconds)
            # This ensures transactions don't stay open indefinitely - PostgreSQL will cancel idle transactions after 20s
            # TCP keepalive settings match the connect_args for consistency
            "options": (
                f"-c statement_timeout={config.DB_STATEMENT_TIMEOUT} "
                f"-c idle_in_transaction_session_timeout=20000 "  # Reduced to 20s for faster cleanup
                f"-c tcp_keepalives_idle=60 "  # Match keepalives_idle
                f"-c tcp_keepalives_interval=10 "  # Match keepalives_interval
                f"-c tcp_keepalives_count=3"  # Match keepalives_count
            ),
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
logger.info(f"  - Pool recycle: {config.DB_POOL_RECYCLE}s ({config.DB_POOL_RECYCLE // 60} minutes)")
logger.info(f"  - Statement timeout: {config.DB_STATEMENT_TIMEOUT}ms")
logger.info(f"  - Idle transaction timeout: 20s")
logger.info(f"  - SSL mode: require")
logger.info(f"  - Keepalives: idle=60s, interval=10s, count=3")

# Track connection invalidation statistics
_connection_invalidation_count = {"total": 0, "ssl_errors": 0, "other_errors": 0}
_invalidation_lock = threading.Lock()

# Add event listeners for connection pool management
@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Called when a connection is retrieved from the pool"""
    # Enhanced connection health check before use
    try:
        # Test connection with a simple query (pool_pre_ping does this, but we add explicit check)
        cursor = dbapi_conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
    except Exception as e:
        # Connection is dead, invalidate it
        error_msg = str(e)
        is_ssl_error = (
            'SSL' in error_msg or
            'connection has been closed' in error_msg.lower() or
            isinstance(e, (psycopg2.OperationalError, psycopg2.InterfaceError))
        )
        
        logger.warning(f"Connection health check failed during checkout, invalidating: {error_msg}")
        connection_record.invalidate(e)
        raise
    
    # Track pool statistics
    pool_status = engine.pool.status()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Connection checked out from pool | Pool status: {pool_status}")

@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Called when a connection is returned to the pool"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Connection checked in to pool")

@event.listens_for(Pool, "invalidate")
def receive_invalidate(dbapi_conn, connection_record, exception):
    """Called when a connection is invalidated - Enhanced logging for SSL errors"""
    error_msg = str(exception) if exception else "Unknown"
    is_ssl_error = (
        'SSL' in error_msg or
        'connection has been closed' in error_msg.lower() or
        'connection reset' in error_msg.lower() or
        'EOF' in error_msg or
        isinstance(exception, (psycopg2.OperationalError, psycopg2.InterfaceError)) if exception else False
    )
    
    # Track invalidation statistics
    with _invalidation_lock:
        _connection_invalidation_count["total"] += 1
        if is_ssl_error:
            _connection_invalidation_count["ssl_errors"] += 1
            logger.warning(f"[POOL] SSL connection invalidated: {error_msg}")
        else:
            _connection_invalidation_count["other_errors"] += 1
            logger.warning(f"[POOL] Connection invalidated: {error_msg}")
    
    # Log pool status after invalidation
    try:
        pool_status = engine.pool.status()
        logger.info(f"[POOL] After invalidation - Pool status: {pool_status}")
    except Exception:
        pass

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Called when a new connection is created"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("New database connection created")

@event.listens_for(Pool, "close")
def receive_close(dbapi_conn, connection_record):
    """Called when a connection is closed"""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Database connection closed")

logger.info("✓ PostgreSQL engine created successfully")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """
    Get database session with proper error handling and connection management.
    Use as FastAPI dependency: db: Session = Depends(get_db)
    
    Enhanced with connection health checks and SSL error handling.
    """
    db = None
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    # Retry loop for getting connection from pool
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            
            # Immediate connection health check
            try:
                db.execute(text("SELECT 1"))
            except (OperationalError, DisconnectionError) as health_error:
                # Connection is dead, invalidate and retry
                error_msg = str(health_error)
                is_ssl_error = (
                    'SSL' in error_msg or
                    'connection has been closed' in error_msg.lower() or
                    'connection reset' in error_msg.lower() or
                    'EOF' in error_msg or
                    (hasattr(health_error, 'orig') and isinstance(health_error.orig, (psycopg2.OperationalError, psycopg2.InterfaceError)))
                )
                
                try:
                    if hasattr(db, 'connection'):
                        db.connection().invalidate()
                    db.close()
                except:
                    pass
                db = None
                
                if attempt < max_retries - 1 and is_ssl_error:
                    logger.warning(
                        f"[DB_HEALTH] Connection health check failed (attempt {attempt + 1}/{max_retries}): {error_msg}. "
                        f"Invalidating connection and retrying..."
                    )
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
            
            break  # Successfully got healthy connection
            
        except Exception as e:
            # Check if it's a pool-related error
            error_str = str(e).lower()
            is_pool_error = any(keyword in error_str for keyword in [
                'pool', 'connection', 'timeout', 'checkout', '_do_get', 
                'could not get connection', '_connectionrecord', 'checkout(pool)'
            ])
            
            if db:
                try:
                    db.close()
                except:
                    pass
                db = None
            
            if attempt < max_retries - 1 and is_pool_error:
                # Pool error, retry after short delay
                logger.warning(
                    f"Database pool error getting connection (attempt {attempt + 1}/{max_retries}): {e}. Retrying..."
                )
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


def get_db_with_retry(max_retries: int = 3, retry_delay: float = 0.1) -> Generator:
    """
    Get database session with retry logic and connection invalidation.
    Invalidates dead connections from pool on SSL/connection errors.
    
    Use this instead of get_db() for critical operations that need resilience.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial retry delay in seconds (default: 0.1)
    
    Yields:
        Database session
    """
    db = None
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            
            # Test connection immediately
            try:
                db.execute(text("SELECT 1"))
            except (OperationalError, DisconnectionError) as health_error:
                # Connection is dead, invalidate and retry
                error_msg = str(health_error)
                is_connection_error = (
                    'connection' in error_msg.lower() or
                    'SSL' in error_msg or
                    'closed' in error_msg.lower() or
                    'reset' in error_msg.lower() or
                    'EOF' in error_msg or
                    (hasattr(health_error, 'orig') and isinstance(health_error.orig, (psycopg2.OperationalError, psycopg2.InterfaceError)))
                )
                
                try:
                    if hasattr(db, 'connection'):
                        db.connection().invalidate()
                    db.close()
                except:
                    pass
                db = None
                
                if attempt < max_retries - 1 and is_connection_error:
                    logger.warning(
                        f"[DB_RETRY] Database connection health check failed (attempt {attempt + 1}/{max_retries}): {error_msg}. "
                        f"Invalidating connection and retrying..."
                    )
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
            
            break  # Successfully got healthy connection
            
        except Exception as e:
            error_msg = str(e).lower()
            is_connection_error = (
                'connection' in error_msg or
                'SSL' in str(e) or
                'closed' in error_msg or
                'reset' in error_msg or
                'EOF' in str(e)
            )
            
            if db:
                try:
                    if hasattr(db, 'connection') and is_connection_error:
                        db.connection().invalidate()
                    db.close()
                except:
                    pass
                db = None
            
            if attempt < max_retries - 1 and is_connection_error:
                logger.warning(
                    f"[DB_RETRY] Database connection error (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Invalidating connection and retrying..."
                )
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                logger.error(f"Failed to get database connection after {max_retries} attempts: {e}")
                raise
    
    try:
        yield db
        db.commit()
    except Exception as e:
        if db:
            try:
                db.rollback()
            except:
                pass
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


def monitor_pool_health():
    """Background thread to monitor and recover from pool issues"""
    while True:
        try:
            time.sleep(60)  # Check every minute
            
            pool_status = engine.pool.status()
            checked_in = pool_status.get('checked_in', 0)
            checked_out = pool_status.get('checked_out', 0)
            overflow = pool_status.get('overflow', 0)
            invalid = pool_status.get('invalid', 0)
            
            # Log pool statistics periodically
            logger.info(
                f"[POOL_MONITOR] Pool status - checked_in={checked_in}, checked_out={checked_out}, "
                f"overflow={overflow}, invalid={invalid}"
            )
            
            # Log invalidation statistics
            with _invalidation_lock:
                total_invalidations = _connection_invalidation_count["total"]
                ssl_invalidations = _connection_invalidation_count["ssl_errors"]
                other_invalidations = _connection_invalidation_count["other_errors"]
            
            if total_invalidations > 0:
                logger.info(
                    f"[POOL_MONITOR] Connection invalidations - total={total_invalidations}, "
                    f"SSL_errors={ssl_invalidations}, other_errors={other_invalidations}"
                )
            
            # If many invalid connections, log warning
            if invalid > 5:
                logger.warning(
                    f"[POOL_MONITOR] Pool has {invalid} invalid connections. "
                    f"This may indicate connection stability issues."
                )
            
            # Test pool health with a simple query
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as e:
                logger.error(f"[POOL_MONITOR] Pool health check failed: {e}")
                # Force pool to recreate connections
                try:
                    engine.pool.invalidate()
                    logger.warning("[POOL_MONITOR] Pool invalidated due to health check failure")
                except Exception as invalidation_error:
                    logger.error(f"[POOL_MONITOR] Failed to invalidate pool: {invalidation_error}")
                
        except Exception as e:
            logger.error(f"[POOL_MONITOR] Pool monitoring error: {e}", exc_info=True)
            time.sleep(60)  # Wait before retrying


# Start pool monitoring in background thread (only in production)
if config.ENV == "production":
    try:
        monitor_thread = threading.Thread(target=monitor_pool_health, daemon=True)
        monitor_thread.start()
        logger.info("✓ Database pool health monitoring started")
    except Exception as monitor_error:
        logger.warning(f"Failed to start pool monitoring thread: {monitor_error}")

