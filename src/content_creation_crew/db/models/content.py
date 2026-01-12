"""
Content generation job and artifact models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..base import Base


class JobStatus(str, enum.Enum):
    """Content job status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(str, enum.Enum):
    """Content type enum"""
    BLOG = "blog"
    SOCIAL = "social"
    AUDIO = "audio"
    VIDEO = "video"


class ContentJob(Base):
    """Content generation job model"""
    __tablename__ = "content_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String, nullable=False)
    formats_requested = Column(JSON, nullable=False)  # List of content types requested
    status = Column(String, nullable=False, default=JobStatus.PENDING.value, index=True)
    idempotency_key = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="content_jobs")
    artifacts = relationship("ContentArtifact", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_content_jobs_status_created", "status", "created_at"),
    )


class ContentArtifact(Base):
    """Content artifact model - stores generated content"""
    __tablename__ = "content_artifacts"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("content_jobs.id"), nullable=False, index=True)
    type = Column(String, nullable=False, index=True)  # 'blog', 'social', 'audio', 'video'
    content_json = Column(JSONB, nullable=True)  # Structured content data (PostgreSQL JSONB)
    content_text = Column(Text, nullable=True)  # Plain text content
    prompt_version = Column(String, nullable=True)  # Version of prompt used
    model_used = Column(String, nullable=True)  # LLM model used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    job = relationship("ContentJob", back_populates="artifacts")
    
    # Indexes
    __table_args__ = (
        Index("idx_content_artifacts_job_type", "job_id", "type"),
    )

