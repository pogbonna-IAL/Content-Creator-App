"""
Content Service - Manages ContentJob and ContentArtifact persistence
"""
import logging
import hashlib
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import HTTPException, status

from ..database import (
    ContentJob,
    ContentArtifact,
    JobStatus,
    User,
    Organization,
    Membership,
    MembershipRole,
)
from .plan_policy import PlanPolicy

logger = logging.getLogger(__name__)


class ContentService:
    """Service for managing content generation jobs and artifacts"""
    
    def __init__(self, db: Session, user: User):
        """
        Initialize ContentService
        
        Args:
            db: Database session
            user: User object
        """
        self.db = db
        self.user = user
        self.policy = PlanPolicy(db, user)
    
    def _get_user_org_id(self) -> int:
        """Get user's organization ID (creates if needed)"""
        # Find user's organization membership
        membership = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).first()
        
        if membership:
            return membership.org_id
        
        # Create organization for user if none exists
        org = Organization(
            name=f"{self.user.email}'s Organization",
            owner_user_id=self.user.id
        )
        self.db.add(org)
        self.db.flush()
        
        # Create membership
        membership = Membership(
            org_id=org.id,
            user_id=self.user.id,
            role=MembershipRole.OWNER.value
        )
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(org)
        
        return org.id
    
    def _generate_idempotency_key(self, topic: str, content_types: List[str]) -> str:
        """Generate idempotency key from topic and content types"""
        normalized_topic = topic.lower().strip()
        normalized_types = sorted(content_types)
        key_string = f"{self.user.id}:{normalized_topic}:{':'.join(normalized_types)}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def create_job(
        self,
        topic: str,
        content_types: List[str],
        idempotency_key: Optional[str] = None
    ) -> ContentJob:
        """
        Create a new content generation job
        
        Args:
            topic: Content topic
            content_types: List of content types to generate
            idempotency_key: Optional idempotency key (auto-generated if not provided)
        
        Returns:
            ContentJob instance
        
        Raises:
            HTTPException: If idempotency key already exists
        """
        org_id = self._get_user_org_id()
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = self._generate_idempotency_key(topic, content_types)
        
        # Check for existing job with same idempotency key
        existing_job = self.db.query(ContentJob).filter(
            ContentJob.idempotency_key == idempotency_key
        ).first()
        
        if existing_job:
            # If job is completed or failed, return it
            if existing_job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                logger.info(f"Found existing job {existing_job.id} with idempotency key {idempotency_key}")
                return existing_job
            # If job is pending or running, raise conflict
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "job_already_exists",
                    "message": f"A job with this idempotency key already exists (job_id: {existing_job.id})",
                    "job_id": existing_job.id,
                    "status": existing_job.status
                }
            )
        
        # Create new job
        job = ContentJob(
            org_id=org_id,
            user_id=self.user.id,
            topic=topic,
            formats_requested=content_types,
            status=JobStatus.PENDING.value,
            idempotency_key=idempotency_key
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created job {job.id} for user {self.user.id}, topic: {topic}")
        return job
    
    def get_job(self, job_id: int, load_artifacts: bool = False) -> Optional[ContentJob]:
        """
        Get job by ID (only if user has access)
        
        Args:
            job_id: Job ID
            load_artifacts: If True, eagerly load artifacts using joinedload (OPTIMIZATION #4)
        """
        query = self.db.query(ContentJob).filter(
            ContentJob.id == job_id,
            ContentJob.user_id == self.user.id
        )
        
        # OPTIMIZATION #4: Use joinedload to fetch artifacts in same query
        if load_artifacts:
            query = query.options(joinedload(ContentJob.artifacts))
        
        job = query.first()
        return job
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContentJob]:
        """List user's jobs with optional filtering"""
        query = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        )
        
        if status:
            query = query.filter(ContentJob.status == status)
        
        return query.order_by(ContentJob.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_job_status(
        self,
        job_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None
    ) -> ContentJob:
        """Update job status"""
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.status = status
        if started_at:
            job.started_at = started_at
        if finished_at:
            job.finished_at = finished_at
        
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def create_artifact(
        self,
        job_id: int,
        artifact_type: str,
        content_text: str,
        content_json: Optional[Dict] = None,
        prompt_version: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> ContentArtifact:
        """
        Create a content artifact
        
        Args:
            job_id: Job ID
            artifact_type: 'blog', 'social', 'audio', 'video', or 'voiceover_audio'
            content_text: Plain text content
            content_json: Optional structured JSON content
            prompt_version: Optional prompt version
            model_used: Optional model name
        
        Returns:
            ContentArtifact instance
        """
        # Verify job exists and belongs to user
        job = self.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Check if artifact already exists for this job and type
        existing = self.db.query(ContentArtifact).filter(
            ContentArtifact.job_id == job_id,
            ContentArtifact.type == artifact_type
        ).first()
        
        if existing:
            # Update existing artifact
            existing.content_text = content_text
            if content_json:
                existing.content_json = content_json
            if prompt_version:
                existing.prompt_version = prompt_version
            if model_used:
                existing.model_used = model_used
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated artifact {existing.id} for job {job_id}, type: {artifact_type}")
            return existing
        
        # Create new artifact
        artifact = ContentArtifact(
            job_id=job_id,
            type=artifact_type,
            content_text=content_text,
            content_json=content_json,
            prompt_version=prompt_version,
            model_used=model_used
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        
        logger.info(f"Created artifact {artifact.id} for job {job_id}, type: {artifact_type}")
        return artifact

