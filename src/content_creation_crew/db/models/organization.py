"""
Organization and Membership models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..base import Base


class MembershipRole(str, enum.Enum):
    """Membership role enum"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    memberships = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    usage_counters = relationship("UsageCounter", back_populates="organization", cascade="all, delete-orphan")
    content_jobs = relationship("ContentJob", back_populates="organization", cascade="all, delete-orphan")
    billing_events = relationship("BillingEvent", back_populates="organization", cascade="all, delete-orphan")


class Membership(Base):
    """Organization membership model"""
    __tablename__ = "memberships"
    
    org_id = Column(Integer, ForeignKey("organizations.id"), primary_key=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False, index=True)
    role = Column(String, nullable=False, default=MembershipRole.MEMBER.value)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

