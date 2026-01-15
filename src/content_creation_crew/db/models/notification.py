"""
Database models for retention notifications
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from ..base import Base


class RetentionNotification(Base):
    """
    Tracks retention notifications sent to users
    Prevents duplicate notifications for the same artifact
    """
    __tablename__ = 'retention_notifications'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    artifact_id = Column(Integer, ForeignKey('content_artifacts.id', ondelete='CASCADE'), nullable=False)
    
    # Notification metadata
    notification_date = Column(Date, nullable=False, index=True)  # Date notification was sent
    expiration_date = Column(Date, nullable=False)  # Expected deletion date
    artifact_type = Column(String(50), nullable=False)
    artifact_topic = Column(String(500), nullable=True)
    
    # Email status
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_failed = Column(Boolean, default=False, nullable=False)
    failure_reason = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="retention_notifications")
    organization = relationship("Organization", backref="retention_notifications")
    artifact = relationship("ContentArtifact", backref="retention_notifications")
    
    # Indexes
    __table_args__ = (
        # Unique constraint: one notification per artifact per date
        Index(
            'idx_retention_notifications_user_artifact',
            'user_id',
            'artifact_id',
            'notification_date',
            unique=True
        ),
        Index('idx_retention_notifications_artifact', 'artifact_id'),
        Index('idx_retention_notifications_notification_date', 'notification_date'),
        Index('idx_retention_notifications_email_status', 'email_sent', 'notification_date'),
    )
    
    def __repr__(self):
        return (
            f"<RetentionNotification(id={self.id}, "
            f"user_id={self.user_id}, "
            f"artifact_id={self.artifact_id}, "
            f"notification_date={self.notification_date}, "
            f"email_sent={self.email_sent})>"
        )

