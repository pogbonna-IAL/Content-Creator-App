"""
Artifact Retention Service (M1)
Automatic deletion of old artifacts based on subscription tier
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ArtifactRetentionService:
    """
    Manages automatic deletion of expired artifacts based on retention policy
    
    Features:
    - Tier-based retention (free: 30d, basic: 90d, pro: 365d, enterprise: unlimited)
    - Safe deletion with transaction rollback
    - Idempotent operations (safe to retry)
    - Dry-run mode for testing
    - GDPR override (delete even enterprise artifacts on user/org deletion)
    - Audit logging for compliance
    """
    
    # Retention policy mapping
    RETENTION_DAYS = {
        'free': 30,
        'basic': 90,
        'pro': 365,
        'enterprise': -1  # Unlimited
    }
    
    def __init__(self, db: Session, dry_run: bool = False):
        """
        Initialize retention service
        
        Args:
            db: Database session
            dry_run: If True, log actions without executing deletions
        """
        self.db = db
        self.dry_run = dry_run
        
        # Load retention configuration from config
        from ..config import config
        
        self.RETENTION_DAYS['free'] = config.RETENTION_DAYS_FREE
        self.RETENTION_DAYS['basic'] = config.RETENTION_DAYS_BASIC
        self.RETENTION_DAYS['pro'] = config.RETENTION_DAYS_PRO
        self.RETENTION_DAYS['enterprise'] = config.RETENTION_DAYS_ENTERPRISE
        
        logger.info(
            f"ArtifactRetentionService initialized (dry_run={dry_run}): "
            f"free={self.RETENTION_DAYS['free']}d, "
            f"basic={self.RETENTION_DAYS['basic']}d, "
            f"pro={self.RETENTION_DAYS['pro']}d, "
            f"enterprise={'unlimited' if self.RETENTION_DAYS['enterprise'] == -1 else f\"{self.RETENTION_DAYS['enterprise']}d\"}"
        )
    
    def compute_retention_days(self, plan: str) -> int:
        """
        Get retention days for a subscription plan
        
        Args:
            plan: Subscription plan (free, basic, pro, enterprise)
        
        Returns:
            Number of days to retain artifacts (-1 for unlimited)
        """
        plan_lower = plan.lower() if plan else 'free'
        return self.RETENTION_DAYS.get(plan_lower, self.RETENTION_DAYS['free'])
    
    def compute_cutoff_date(self, plan: str) -> Optional[datetime]:
        """
        Compute cutoff date for artifact retention
        
        Args:
            plan: Subscription plan
        
        Returns:
            Cutoff datetime (artifacts older than this should be deleted)
            None if plan has unlimited retention
        """
        retention_days = self.compute_retention_days(plan)
        
        if retention_days == -1:
            return None  # Unlimited retention
        
        return datetime.utcnow() - timedelta(days=retention_days)
    
    def list_expired_artifacts(
        self,
        cutoff_date: datetime,
        org_id: Optional[int] = None,
        plan: Optional[str] = None
    ) -> List[Any]:
        """
        List artifacts that are expired and eligible for deletion
        
        Args:
            cutoff_date: Delete artifacts older than this date
            org_id: Filter by organization ID (optional)
            plan: Plan name for logging (optional)
        
        Returns:
            List of expired ContentArtifact objects
        """
        from ..database import ContentArtifact, ContentJob, User, Organization, OrganizationMember
        
        try:
            # Query expired artifacts
            query = self.db.query(ContentArtifact).join(
                ContentJob, ContentArtifact.job_id == ContentJob.id
            ).join(
                User, ContentJob.user_id == User.id
            )
            
            # Filter by cutoff date
            query = query.filter(ContentArtifact.created_at < cutoff_date)
            
            # Filter by organization if specified
            if org_id:
                query = query.join(
                    OrganizationMember, User.id == OrganizationMember.user_id
                ).filter(
                    OrganizationMember.organization_id == org_id
                )
            
            expired_artifacts = query.all()
            
            logger.info(
                f"Found {len(expired_artifacts)} expired artifacts "
                f"(cutoff={cutoff_date.isoformat()}, "
                f"org_id={org_id}, plan={plan})"
            )
            
            return expired_artifacts
        
        except Exception as e:
            logger.error(f"Error listing expired artifacts: {e}", exc_info=True)
            return []
    
    def delete_artifact_files(self, artifact: Any) -> Tuple[bool, int]:
        """
        Delete storage files associated with an artifact
        
        Args:
            artifact: ContentArtifact object
        
        Returns:
            Tuple of (success, bytes_deleted)
        """
        from ..services.storage_provider import get_storage_provider
        
        storage = get_storage_provider()
        bytes_deleted = 0
        
        try:
            # Get storage key from artifact
            storage_key = artifact.storage_key
            
            if not storage_key:
                logger.debug(f"Artifact {artifact.id} has no storage key, skipping file deletion")
                return True, 0
            
            # Get file size before deletion (if available)
            try:
                file_data = storage.get(storage_key)
                if file_data:
                    bytes_deleted = len(file_data)
            except Exception:
                pass  # File might already be deleted or not accessible
            
            # Delete file
            if not self.dry_run:
                success = storage.delete(storage_key)
                
                if success:
                    logger.info(f"Deleted storage file: {storage_key} ({bytes_deleted} bytes)")
                    return True, bytes_deleted
                else:
                    logger.warning(f"Failed to delete storage file: {storage_key}")
                    return False, 0
            else:
                logger.info(f"[DRY RUN] Would delete storage file: {storage_key} ({bytes_deleted} bytes)")
                return True, bytes_deleted
        
        except Exception as e:
            logger.error(f"Error deleting artifact files for artifact {artifact.id}: {e}", exc_info=True)
            return False, 0
    
    def delete_artifact_records(self, artifacts: List[Any]) -> Tuple[int, int]:
        """
        Delete artifact database records with transaction safety
        
        Args:
            artifacts: List of ContentArtifact objects to delete
        
        Returns:
            Tuple of (deleted_count, failed_count)
        """
        deleted_count = 0
        failed_count = 0
        
        for artifact in artifacts:
            try:
                if not self.dry_run:
                    # Delete in transaction
                    self.db.delete(artifact)
                    self.db.flush()  # Flush but don't commit yet
                    
                    deleted_count += 1
                    logger.debug(f"Deleted artifact record: {artifact.id}")
                else:
                    logger.info(f"[DRY RUN] Would delete artifact record: {artifact.id}")
                    deleted_count += 1
            
            except Exception as e:
                logger.error(f"Error deleting artifact record {artifact.id}: {e}", exc_info=True)
                failed_count += 1
                # Don't rollback here, continue with other artifacts
        
        return deleted_count, failed_count
    
    def cleanup_expired_artifacts(
        self,
        org_id: int,
        plan: str,
        gdpr_override: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up expired artifacts for an organization
        
        Args:
            org_id: Organization ID
            plan: Subscription plan
            gdpr_override: If True, delete even enterprise artifacts (for GDPR)
        
        Returns:
            Dict with cleanup statistics
        """
        stats = {
            "org_id": org_id,
            "plan": plan,
            "retention_days": self.compute_retention_days(plan),
            "artifacts_found": 0,
            "artifacts_deleted": 0,
            "artifacts_failed": 0,
            "bytes_freed": 0,
            "dry_run": self.dry_run,
            "gdpr_override": gdpr_override
        }
        
        try:
            # Check if retention applies
            if stats["retention_days"] == -1 and not gdpr_override:
                logger.info(f"Org {org_id} has unlimited retention (plan={plan}), skipping cleanup")
                return stats
            
            # Compute cutoff date
            cutoff_date = self.compute_cutoff_date(plan)
            
            if gdpr_override:
                # For GDPR deletion, delete ALL artifacts regardless of age
                cutoff_date = datetime.utcnow() + timedelta(days=1)  # Future date = all artifacts
                logger.info(f"GDPR override active for org {org_id}, deleting ALL artifacts")
            
            if not cutoff_date:
                logger.info(f"No cutoff date for org {org_id} (plan={plan}), skipping cleanup")
                return stats
            
            # Find expired artifacts
            expired_artifacts = self.list_expired_artifacts(cutoff_date, org_id, plan)
            stats["artifacts_found"] = len(expired_artifacts)
            
            if not expired_artifacts:
                logger.info(f"No expired artifacts for org {org_id}")
                return stats
            
            # Delete files first, then records
            for artifact in expired_artifacts:
                # Delete storage files
                file_success, bytes_deleted = self.delete_artifact_files(artifact)
                
                if file_success:
                    stats["bytes_freed"] += bytes_deleted
            
            # Delete artifact records in batch
            deleted, failed = self.delete_artifact_records(expired_artifacts)
            stats["artifacts_deleted"] = deleted
            stats["artifacts_failed"] = failed
            
            # Commit transaction
            if not self.dry_run and deleted > 0:
                self.db.commit()
                logger.info(
                    f"Committed deletion of {deleted} artifacts for org {org_id} "
                    f"({stats['bytes_freed']} bytes freed)"
                )
            elif self.dry_run:
                logger.info(
                    f"[DRY RUN] Would commit deletion of {deleted} artifacts for org {org_id}"
                )
            
            return stats
        
        except Exception as e:
            logger.error(f"Error during artifact cleanup for org {org_id}: {e}", exc_info=True)
            if not self.dry_run:
                self.db.rollback()
            stats["artifacts_failed"] = stats["artifacts_found"]
            return stats
    
    def cleanup_all_organizations(self) -> Dict[str, Any]:
        """
        Run retention cleanup for all organizations
        
        Returns:
            Dict with overall statistics
        """
        from ..database import Organization, Subscription
        
        overall_stats = {
            "total_orgs": 0,
            "total_artifacts_found": 0,
            "total_artifacts_deleted": 0,
            "total_artifacts_failed": 0,
            "total_bytes_freed": 0,
            "dry_run": self.dry_run,
            "org_stats": []
        }
        
        try:
            # Get all organizations with their active subscriptions
            orgs = self.db.query(Organization).all()
            overall_stats["total_orgs"] = len(orgs)
            
            logger.info(f"Starting retention cleanup for {len(orgs)} organizations")
            
            for org in orgs:
                # Get active subscription
                active_sub = self.db.query(Subscription).filter(
                    Subscription.organization_id == org.id,
                    Subscription.status == 'active'
                ).first()
                
                plan = active_sub.plan if active_sub else 'free'
                
                # Run cleanup for this org
                org_stats = self.cleanup_expired_artifacts(org.id, plan, gdpr_override=False)
                
                # Aggregate statistics
                overall_stats["total_artifacts_found"] += org_stats["artifacts_found"]
                overall_stats["total_artifacts_deleted"] += org_stats["artifacts_deleted"]
                overall_stats["total_artifacts_failed"] += org_stats["artifacts_failed"]
                overall_stats["total_bytes_freed"] += org_stats["bytes_freed"]
                overall_stats["org_stats"].append(org_stats)
            
            logger.info(
                f"Retention cleanup complete: "
                f"{overall_stats['total_artifacts_deleted']} artifacts deleted, "
                f"{overall_stats['total_bytes_freed']} bytes freed"
            )
            
            return overall_stats
        
        except Exception as e:
            logger.error(f"Error during retention cleanup: {e}", exc_info=True)
            return overall_stats


def get_retention_service(db: Session, dry_run: bool = False) -> ArtifactRetentionService:
    """
    Get artifact retention service instance
    
    Args:
        db: Database session
        dry_run: Enable dry-run mode
    
    Returns:
        ArtifactRetentionService instance
    """
    from ..config import config
    
    # Override dry_run with config if set
    if config.RETENTION_DRY_RUN:
        dry_run = True
        logger.warning("RETENTION_DRY_RUN is enabled in config - no artifacts will be deleted")
    
    return ArtifactRetentionService(db, dry_run=dry_run)

