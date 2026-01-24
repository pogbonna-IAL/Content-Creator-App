"""
User and Session models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    full_name = Column(String, nullable=True)
    provider = Column(String, nullable=True)  # 'google', 'facebook', 'github', 'email' (backward compat: also auth_provider)
    provider_id = Column(String, nullable=True)  # User ID from OAuth provider
    
    # Alias for backward compatibility
    @property
    def auth_provider(self):
        return self.provider
    
    @auth_provider.setter
    def auth_provider(self, value):
        self.provider = value
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Admin flag - defaults to False for backward compatibility
    is_admin = Column(Boolean, default=False, nullable=False, index=True)
    
    # Email Verification (S8)
    email_verified = Column(Boolean, default=False, nullable=False)  # New field for explicit tracking
    email_verification_token = Column(String, nullable=True, index=True)
    email_verification_sent_at = Column(DateTime, nullable=True)
    
    # GDPR deletion
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """User session model for token management"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

