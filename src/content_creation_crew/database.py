"""
Database models and setup for authentication and subscriptions
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta

# Database URL from environment variable, default to SQLite
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./content_crew.db")

# Configure engine based on database type
if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL connection
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
else:
    # SQLite connection
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
    try:
        # Run migrations using Alembic
        from alembic.config import Config
        from alembic import command
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info("Running database migrations...")
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        # Fallback to create_all if migrations fail (for backwards compatibility)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Migration failed: {e}. Falling back to create_all.")
        Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

