"""
GDPR Data Export Service
Exports all user data in machine-readable format
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import User, ContentJob, ContentArtifact
from ..db.models.organization import Organization, Membership
from ..db.models.subscription import Subscription, UsageCounter
from ..db.models.billing import BillingEvent

logger = logging.getLogger(__name__)

# Current export schema version (for future compatibility)
EXPORT_SCHEMA_VERSION = "1.0"


class GDPRExportService:
    """Service for exporting user data in GDPR-compliant format"""
    
    def __init__(self, db: Session, user: User):
        """
        Initialize export service
        
        Args:
            db: Database session
            user: User requesting export
        """
        self.db = db
        self.user = user
    
    def export_user_data(self) -> Dict[str, Any]:
        """
        Export all user data in machine-readable format
        
        Returns:
            Dictionary containing all user data
        """
        logger.info(f"Starting GDPR data export for user {self.user.id}")
        
        export_data = {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_date": datetime.utcnow().isoformat(),
            "user_id": self.user.id,
            "profile": self._export_profile(),
            "memberships": self._export_memberships(),
            "organizations": self._export_organizations(),
            "subscriptions": self._export_subscriptions(),
            "usage": self._export_usage(),
            "billing_events": self._export_billing_events(),
            "content_jobs": self._export_content_jobs(),
            "artifact_references": self._export_artifact_references(),
            "statistics": self._export_statistics(),
        }
        
        logger.info(f"GDPR data export completed for user {self.user.id}")
        return export_data
    
    def _export_profile(self) -> Dict[str, Any]:
        """Export user profile data"""
        return {
            "id": self.user.id,
            "email": self.user.email,
            "full_name": self.user.full_name,
            "provider": self.user.provider,
            "provider_id": self.user.provider_id if self.user.provider != "email" else None,
            "is_active": self.user.is_active,
            "is_verified": self.user.is_verified,
            "created_at": self.user.created_at.isoformat() if self.user.created_at else None,
            "updated_at": self.user.updated_at.isoformat() if self.user.updated_at else None,
        }
    
    def _export_memberships(self) -> List[Dict[str, Any]]:
        """Export user's organization memberships"""
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        return [
            {
                "org_id": m.org_id,
                "role": m.role,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "updated_at": m.updated_at.isoformat() if m.updated_at else None,
            }
            for m in memberships
        ]
    
    def _export_organizations(self) -> List[Dict[str, Any]]:
        """Export organizations where user is a member"""
        # Get organizations through memberships
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        organizations = self.db.query(Organization).filter(
            Organization.id.in_(org_ids)
        ).all() if org_ids else []
        
        return [
            {
                "id": org.id,
                "name": org.name,
                "owner_user_id": org.owner_user_id,
                "is_owner": org.owner_user_id == self.user.id,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "updated_at": org.updated_at.isoformat() if org.updated_at else None,
            }
            for org in organizations
        ]
    
    def _export_subscriptions(self) -> List[Dict[str, Any]]:
        """Export subscription data for user's organizations"""
        # Get organizations where user is a member
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        subscriptions = self.db.query(Subscription).filter(
            Subscription.org_id.in_(org_ids)
        ).all() if org_ids else []
        
        return [
            {
                "id": sub.id,
                "org_id": sub.org_id,
                "plan": sub.plan,
                "status": sub.status,
                "provider": sub.provider,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
            }
            for sub in subscriptions
        ]
    
    def _export_usage(self) -> List[Dict[str, Any]]:
        """Export usage counter data"""
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        usage_counters = self.db.query(UsageCounter).filter(
            UsageCounter.org_id.in_(org_ids)
        ).all() if org_ids else []
        
        return [
            {
                "org_id": uc.org_id,
                "period_month": uc.period_month,
                "blog_count": uc.blog_count,
                "social_count": uc.social_count,
                "audio_count": uc.audio_count,
                "video_count": uc.video_count,
                "voiceover_count": uc.voiceover_count,
                "video_render_count": uc.video_render_count,
                "created_at": uc.created_at.isoformat() if uc.created_at else None,
                "updated_at": uc.updated_at.isoformat() if uc.updated_at else None,
            }
            for uc in usage_counters
        ]
    
    def _export_billing_events(self) -> List[Dict[str, Any]]:
        """Export billing events (anonymized)"""
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        billing_events = self.db.query(BillingEvent).filter(
            BillingEvent.org_id.in_(org_ids)
        ).all() if org_ids else []
        
        return [
            {
                "id": event.id,
                "org_id": event.org_id,
                "provider": event.provider,
                "event_type": event.event_type,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                # Do not export full payload (may contain sensitive payment info)
                # Only export metadata
                "metadata": {
                    "event_id": event.provider_event_id,
                    "type": event.event_type,
                }
            }
            for event in billing_events
        ]
    
    def _export_content_jobs(self) -> List[Dict[str, Any]]:
        """Export content generation jobs"""
        jobs = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        ).order_by(ContentJob.created_at.desc()).all()
        
        return [
            {
                "id": job.id,
                "org_id": job.org_id,
                "topic": job.topic,
                "formats_requested": job.formats_requested,
                "status": job.status,
                "idempotency_key": job.idempotency_key,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "artifact_count": len(job.artifacts) if job.artifacts else 0,
            }
            for job in jobs
        ]
    
    def _export_artifact_references(self) -> List[Dict[str, Any]]:
        """Export artifact metadata and file references (not full content)"""
        jobs = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        ).all()
        
        job_ids = [job.id for job in jobs]
        artifacts = self.db.query(ContentArtifact).filter(
            ContentArtifact.job_id.in_(job_ids)
        ).all() if job_ids else []
        
        artifact_refs = []
        for artifact in artifacts:
            ref = {
                "id": artifact.id,
                "job_id": artifact.job_id,
                "type": artifact.type,
                "prompt_version": artifact.prompt_version,
                "model_used": artifact.model_used,
                "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
                "has_text": bool(artifact.content_text),
                "text_preview": artifact.content_text[:200] if artifact.content_text else None,
            }
            
            # Add metadata for media artifacts
            if artifact.type in ['voiceover_audio', 'final_video', 'video_clip', 'storyboard_image']:
                if artifact.content_json:
                    ref["metadata"] = {
                        "storage_key": artifact.content_json.get("storage_key"),
                        "format": artifact.content_json.get("format"),
                        "duration_sec": artifact.content_json.get("duration_sec"),
                        "resolution": artifact.content_json.get("resolution"),
                        "provider": artifact.content_json.get("provider"),
                    }
            
            artifact_refs.append(ref)
        
        return artifact_refs
    
    def _export_statistics(self) -> Dict[str, Any]:
        """Export summary statistics"""
        jobs = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        ).all()
        
        job_ids = [job.id for job in jobs]
        artifacts = self.db.query(ContentArtifact).filter(
            ContentArtifact.job_id.in_(job_ids)
        ).all() if job_ids else []
        
        return {
            "total_jobs": len(jobs),
            "total_artifacts": len(artifacts),
            "artifacts_by_type": self._count_artifacts_by_type(artifacts),
            "jobs_by_status": self._count_jobs_by_status(jobs),
        }
    
    def _count_artifacts_by_type(self, artifacts: List[ContentArtifact]) -> Dict[str, int]:
        """Count artifacts by type"""
        counts = {}
        for artifact in artifacts:
            counts[artifact.type] = counts.get(artifact.type, 0) + 1
        return counts
    
    def _count_jobs_by_status(self, jobs: List[ContentJob]) -> Dict[str, int]:
        """Count jobs by status"""
        counts = {}
        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        return counts

