"""
User Model Preference model for storing user-specific model preferences per content type
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


class UserModelPreference(Base):
    """User-specific model preferences per content type"""
    __tablename__ = "user_model_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_type = Column(String, nullable=False)  # 'blog', 'social', 'audio', 'video'
    model_name = Column(String, nullable=False)  # e.g., 'gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Track which admin set this
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="model_preferences")
    created_by_admin = relationship("User", foreign_keys=[created_by_admin_id])
    
    # Unique constraint: one preference per user per content type
    __table_args__ = (
        UniqueConstraint('user_id', 'content_type', name='uq_user_content_type'),
    )
