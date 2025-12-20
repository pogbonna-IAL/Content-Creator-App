"""
Database models and setup for authentication and subscriptions
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import Pool
from datetime import datetime, timedelta

# Database URL from environment variable, default to SQLite
import os
import logging

logger = logging.getLogger(__name__)

# Get DATABASE_URL from environment
# On Railway, this is automatically provided when PostgreSQL service is linked
# Format: postgresql://user:password@hostname:port/database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content_crew.db")

# Log DATABASE_URL info (without exposing credentials)
def _log_database_url_info():
    """Log database URL information without exposing credentials"""
    if DATABASE_URL.startswith("postgresql"):
        # Parse URL to show structure without credentials
        try:
            # Extract hostname from URL
            if "@" in DATABASE_URL:
                host_part = DATABASE_URL.split("@")[1].split("/")[0]
                if ":" in host_part:
                    hostname = host_part.split(":")[0]
                else:
                    hostname = host_part
                logger.info(f"DATABASE_URL configured for PostgreSQL (host: {hostname})")
                
                # Check if using Docker Compose hostname (won't work on Railway)
                if hostname == "db":
                    logger.error("⚠️  DATABASE_URL uses 'db' hostname (Docker Compose) - this won't work on Railway!")
                    logger.error("⚠️  Railway provides DATABASE_URL automatically when PostgreSQL service is linked")
                    logger.error("⚠️  Check Railway dashboard: Backend service → Variables → DATABASE_URL")
            else:
                logger.warning("DATABASE_URL format appears incorrect (missing @)")
        except Exception:
            logger.warning("Could not parse DATABASE_URL for logging")
    elif DATABASE_URL.startswith("sqlite"):
        logger.info("DATABASE_URL configured for SQLite (local development)")
    else:
        logger.warning(f"DATABASE_URL uses unknown format: {DATABASE_URL[:20]}...")

# Log database URL info on module import
_log_database_url_info()

# Configure engine based on database type with better error handling
def create_database_engine():
    """Create database engine with proper error handling"""
    try:
        if DATABASE_URL.startswith("postgresql"):
            # PostgreSQL connection with connection pool settings
            # Optimized for Railway deployment - smaller pool, better error handling
            engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,  # Verify connections before using (reconnects if needed)
                pool_size=2,  # Minimal pool size for Railway (very small instances)
                max_overflow=3,  # Minimal overflow
                pool_recycle=900,  # Recycle connections after 15 minutes (very aggressive)
                pool_timeout=10,  # Reduced timeout to fail faster
                echo=False,  # Disable SQL logging for performance
                # Use NullPool for very constrained environments (uncomment if still having issues)
                # poolclass=NullPool,  # Disables pooling entirely - use only if pool issues persist
                connect_args={
                    "connect_timeout": 3,  # Very short connection timeout
                    "keepalives": 1,  # Enable TCP keepalives
                    "keepalives_idle": 30,  # Start keepalives after 30 seconds idle
                    "keepalives_interval": 10,  # Send keepalive every 10 seconds
                    "keepalives_count": 3,  # Reduced keepalive failures before disconnect
                    # Add application_name for better connection tracking
                    "application_name": "content_creation_crew",
                }
            )
            
            # Add event listeners for better connection pool error handling
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Set connection-level settings"""
                pass  # PostgreSQL doesn't need pragma settings
            
            @event.listens_for(Pool, "checkout")
            def receive_checkout(dbapi_conn, connection_record, connection_proxy):
                """Called when a connection is retrieved from the pool"""
                try:
                    # Connection is already validated by pool_pre_ping
                    # But we can add additional validation here if needed
                    logger.debug("Connection checked out from pool")
                except Exception as e:
                    logger.warning(f"Error during connection checkout: {e}")
                    # Don't raise - let SQLAlchemy handle it
            
            @event.listens_for(Pool, "checkin")
            def receive_checkin(dbapi_conn, connection_record):
                """Called when a connection is returned to the pool"""
                logger.debug("Connection checked in to pool")
            
            @event.listens_for(Pool, "invalidate")
            def receive_invalidate(dbapi_conn, connection_record, exception):
                """Called when a connection is invalidated"""
                logger.warning(f"Connection invalidated: {exception}")
            
            logger.info("PostgreSQL engine created successfully with optimized pool settings and event listeners")
        else:
            # SQLite connection
            engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
            logger.info("SQLite engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        # For PostgreSQL, if connection fails, fall back to SQLite for development
        if DATABASE_URL.startswith("postgresql"):
            logger.warning("PostgreSQL connection failed, falling back to SQLite")
            fallback_url = "sqlite:///./content_crew.db"
            return create_engine(fallback_url, connect_args={"check_same_thread": False})
        raise

# Create engine with error handling and fallback to NullPool if needed
def create_engine_with_fallback():
    """Create database engine with fallback options"""
    try:
        return create_database_engine()
    except Exception as e:
        logger.error(f"Critical: Could not create database engine: {e}", exc_info=True)
        
        # If PostgreSQL and pool issues, try NullPool (no pooling)
        if DATABASE_URL.startswith("postgresql"):
            logger.warning("Attempting to create engine with NullPool (no connection pooling)...")
            try:
                from sqlalchemy.pool import NullPool
                return create_engine(
                    DATABASE_URL,
                    poolclass=NullPool,  # No pooling - new connection for each request
                    pool_pre_ping=True,
                    connect_args={
                        "connect_timeout": 3,
                        "keepalives": 1,
                        "keepalives_idle": 30,
                        "keepalives_interval": 10,
                        "keepalives_count": 3,
                        "application_name": "content_creation_crew",
                    }
                )
            except Exception as null_pool_error:
                logger.error(f"Failed to create engine with NullPool: {null_pool_error}", exc_info=True)
        
        # Last resort: SQLite
        logger.warning("Falling back to SQLite database...")
        return create_engine("sqlite:///./content_crew.db", connect_args={"check_same_thread": False})

# Create engine with error handling
try:
    engine = create_engine_with_fallback()
except Exception as e:
    logger.error(f"Critical: Could not create any database engine: {e}", exc_info=True)
    # Absolute last resort: SQLite
    engine = create_engine("sqlite:///./content_crew.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # OAuth provider information
    provider = Column(String, nullable=True)  # 'google', 'facebook', 'github', 'email'
    provider_id = Column(String, nullable=True)  # User ID from OAuth provider
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    # Subscription relationship removed for future implementation
    # subscription = relationship("UserSubscription", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")


class SubscriptionTier(Base):
    """Subscription tier definitions"""
    __tablename__ = "subscription_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # 'free', 'basic', 'pro', 'enterprise'
    display_name = Column(String, nullable=False)
    # Pricing fields kept in schema for future implementation but not used
    price_monthly = Column(Integer, default=0, nullable=True)  # Price in cents - for future payment integration
    price_yearly = Column(Integer, default=0, nullable=True)  # Price in cents - for future payment integration
    features = Column(JSON)  # List of feature strings
    limits = Column(JSON)  # Dict of content type limits
    content_types = Column(JSON)  # List of available content types
    model = Column(String)  # LLM model to use
    max_parallel_tasks = Column(Integer, default=1)
    priority_processing = Column(Boolean, default=False)
    api_access = Column(Boolean, default=False)
    api_rate_limit = Column(Integer, nullable=True)  # Requests per day, null = unlimited
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - commented out for future implementation
    # subscriptions = relationship("UserSubscription", back_populates="tier")


# Subscription management model removed for future implementation
# This will be added when subscription management is integrated with pricing

class UserSubscription(Base):
    """User subscription records - For future implementation with pricing"""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False)
    status = Column(String, nullable=False, default='active')  # 'active', 'cancelled', 'expired', 'past_due'
    # Default to current time for period start, and 30 days later for period end
    current_period_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False, index=True)
    cancel_at_period_end = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    # Payment integration fields kept in schema for future implementation but not used
    stripe_subscription_id = Column(String, nullable=True, unique=True, index=True)  # For future payment integration
    stripe_customer_id = Column(String, nullable=True, index=True)  # For future payment integration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - commented out for now
    # user = relationship("User", back_populates="subscription")
    # tier = relationship("SubscriptionTier", back_populates="subscriptions")
    # usage_records = relationship("UsageTracking", back_populates="subscription")
    
    def __init__(self, **kwargs):
        """Initialize subscription with default billing period if not provided"""
        # Set default billing period if not provided
        if 'current_period_start' not in kwargs:
            kwargs['current_period_start'] = datetime.utcnow()
        if 'current_period_end' not in kwargs:
            # Default to 30 days from start
            start = kwargs.get('current_period_start', datetime.utcnow())
            if isinstance(start, datetime):
                kwargs['current_period_end'] = start + timedelta(days=30)
            else:
                kwargs['current_period_end'] = datetime.utcnow() + timedelta(days=30)
        super().__init__(**kwargs)


# Usage tracking model removed for future implementation
# This will be added when subscription management is integrated with pricing

class UsageTracking(Base):
    """Track content generation usage per billing period - For future implementation"""
    __tablename__ = "usage_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True)
    content_type = Column(String, nullable=False)  # 'blog', 'social', 'audio', 'video'
    generation_count = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - commented out for now
    # user = relationship("User")
    # subscription = relationship("UserSubscription", back_populates="usage_records")


def init_db():
    """Initialize database tables using Alembic migrations"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Test database connection first
    try:
        logger.info("Testing database connection...")
        
        # Log connection attempt details (without credentials)
        if DATABASE_URL.startswith("postgresql"):
            try:
                if "@" in DATABASE_URL:
                    host_part = DATABASE_URL.split("@")[1].split("/")[0]
                    if ":" in host_part:
                        hostname = host_part.split(":")[0]
                    else:
                        hostname = host_part
                    logger.info(f"Attempting to connect to PostgreSQL at: {hostname}")
                    
                    # Check for Docker Compose hostname
                    if hostname == "db":
                        logger.error("=" * 60)
                        logger.error("❌ RAILWAY DATABASE CONNECTION ERROR")
                        logger.error("=" * 60)
                        logger.error("DATABASE_URL uses 'db' hostname (Docker Compose service name)")
                        logger.error("This hostname only works in Docker Compose, NOT on Railway!")
                        logger.error("")
                        logger.error("SOLUTION:")
                        logger.error("1. Go to Railway Dashboard")
                        logger.error("2. Select your Backend service")
                        logger.error("3. Go to 'Variables' tab")
                        logger.error("4. Check if DATABASE_URL is set")
                        logger.error("5. If not set, link PostgreSQL service:")
                        logger.error("   - Go to PostgreSQL service")
                        logger.error("   - Click 'Connect' or 'Add Service'")
                        logger.error("   - Select your Backend service")
                        logger.error("   - Railway will automatically add DATABASE_URL")
                        logger.error("=" * 60)
                        raise ConnectionError(
                            "DATABASE_URL uses 'db' hostname - not valid on Railway. "
                            "Link PostgreSQL service to Backend service in Railway dashboard."
                        )
            except ConnectionError:
                # Re-raise connection errors (like the 'db' hostname error)
                raise
            except Exception as parse_error:
                logger.warning(f"Could not parse DATABASE_URL: {parse_error}")
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection test successful")
    except ConnectionError:
        # Re-raise connection errors (like the 'db' hostname error)
        raise
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"✗ Database connection test failed: {e}", exc_info=True)
        
        # Provide helpful error messages
        if "could not translate host name" in error_msg or "name or service not known" in error_msg:
            logger.error("=" * 60)
            logger.error("❌ DATABASE HOSTNAME RESOLUTION ERROR")
            logger.error("=" * 60)
            logger.error("The database hostname cannot be resolved.")
            logger.error("")
            logger.error("POSSIBLE CAUSES:")
            logger.error("1. DATABASE_URL uses Docker Compose hostname (e.g., 'db')")
            logger.error("2. PostgreSQL service not linked to Backend service on Railway")
            logger.error("3. DATABASE_URL environment variable not set correctly")
            logger.error("")
            logger.error("SOLUTION:")
            logger.error("1. Go to Railway Dashboard → Backend service → Variables")
            logger.error("2. Verify DATABASE_URL is set (should start with 'postgresql://')")
            logger.error("3. If missing, link PostgreSQL service to Backend:")
            logger.error("   - PostgreSQL service → Connect → Select Backend service")
            logger.error("4. Railway will automatically set DATABASE_URL")
            logger.error("=" * 60)
        
        logger.warning("Skipping database initialization - will retry on first request")
        logger.warning("Application will continue but database features may not work until connection is established")
        return
    
    try:
        # Run migrations using Alembic
        from alembic.config import Config
        from alembic import command
        
        logger.info("Running database migrations...")
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        # Fallback to create_all if migrations fail (for backwards compatibility)
        logger.warning(f"Migration failed: {e}. Falling back to create_all.")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created using create_all")
        except Exception as create_error:
            logger.error(f"Failed to create database tables: {create_error}", exc_info=True)
            logger.warning("Database initialization failed - application will continue but database features may not work")


def get_db():
    """Get database session with proper error handling and connection management"""
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
            error_traceback = str(e)
            
            # Check for various pool-related errors including checkout
            is_pool_error = any(keyword in error_str for keyword in [
                'pool', 'connection', 'timeout', 'checkout', '_do_get', 
                'could not get connection', '_connectionrecord', 'checkout(pool)'
            ])
            
            # Also check traceback for pool-related patterns
            if not is_pool_error and ('checkout' in error_traceback.lower() or '_connectionrecord' in error_traceback.lower()):
                is_pool_error = True
            
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
                    logger.error("3. DATABASE_URL incorrect (check Railway Variables)")
                    logger.error("4. PostgreSQL service not properly linked")
                    logger.error("")
                    logger.error("SOLUTION:")
                    logger.error("1. Verify DATABASE_URL is correct in Railway Variables")
                    logger.error("2. Ensure PostgreSQL service is linked to Backend")
                    logger.error("3. Check PostgreSQL service logs for connectivity issues")
                    logger.error("4. Consider using NullPool if pool issues persist")
                    logger.error("=" * 60)
                logger.error(f"Failed to get database connection: {e}", exc_info=True)
                raise
    
    # Now yield the session (this is the generator part)
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
                logger.warning(f"Error closing database session: {e}", exc_info=True)

