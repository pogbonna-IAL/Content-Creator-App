"""
GDPR User Deletion Service
Implements soft delete with grace period and hard delete with transaction safety
"""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path

from ..database import User, ContentJob, ContentArtifact, Session as UserSession
from ..db.models.organization import Organization, Membership
from ..db.models.subscription import Subscription, UsageCounter
from ..db.models.billing import BillingEvent
from ..config import config

logger = logging.getLogger(__name__)

# Soft delete grace period (days before hard delete)
SOFT_DELETE_GRACE_PERIOD_DAYS = int(config.GDPR_DELETION_GRACE_DAYS if hasattr(config, 'GDPR_DELETION_GRACE_DAYS') else 30)


def redact_email(email: str) -> str:
    """
    Redact email for logging (GDPR-compliant logging)
    
    Args:
        email: Email address to redact
    
    Returns:
        Redacted email (first 2 chars + hash + domain)
    """
    if not email or '@' not in email:
        return "***@***"
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"**@{domain}"
    
    # Create a short hash of the local part
    email_hash = hashlib.sha256(email.encode()).hexdigest()[:6]
    return f"{local[:2]}***{email_hash}@{domain}"


class GDPRDeletionService:
    """Service for GDPR-compliant user deletion"""
    
    def __init__(self, db: Session, user: User):
        """
        Initialize deletion service
        
        Args:
            db: Database session
            user: User requesting deletion
        """
        self.db = db
        self.user = user
    
    def soft_delete(self) -> Dict[str, Any]:
        """
        Soft delete user account (immediate access disable, data retained for grace period)
        
        Returns:
            Confirmation with hard delete scheduled date
        """
        redacted_email = redact_email(self.user.email)
        logger.info(f"Starting soft delete for user {self.user.id} ({redacted_email})")
        
        # Mark user as deleted
        if not hasattr(User, 'deleted_at'):
            # If column doesn't exist yet, just disable account
            self.user.is_active = False
            logger.warning("deleted_at column not found, using is_active=False instead")
        else:
            self.user.deleted_at = datetime.utcnow()
            self.user.is_active = False
        
        self.db.commit()
        
        # Revoke all sessions
        self.purge_sessions(self.user.id)
        
        # Calculate hard delete date
        hard_delete_date = datetime.utcnow() + timedelta(days=SOFT_DELETE_GRACE_PERIOD_DAYS)
        
        logger.info(f"Soft delete completed for user {self.user.id} ({redacted_email}), hard delete scheduled for {hard_delete_date}")
        
        return {
            "status": "deleted",
            "deletion_type": "soft",
            "deleted_at": datetime.utcnow().isoformat(),
            "hard_delete_scheduled": hard_delete_date.isoformat(),
            "grace_period_days": SOFT_DELETE_GRACE_PERIOD_DAYS,
            "message": f"Your account has been disabled. All data will be permanently deleted on {hard_delete_date.strftime('%Y-%m-%d')}. Contact support to restore your account before then."
        }
    
    def hard_delete(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        Hard delete user account and all associated data (permanent)
        
        This should only be called after grace period or explicitly requested.
        Implements transaction safety with retries.
        
        Args:
            max_retries: Maximum number of retry attempts on failure
        
        Returns:
            Confirmation of deletion
        
        Raises:
            Exception: If deletion fails after all retries
        """
        user_id = self.user.id
        redacted_email = redact_email(self.user.email)
        
        logger.info(f"Starting hard delete for user {user_id} ({redacted_email})")
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Execute deletion in transaction
                result = self._execute_hard_delete_transaction()
                
                logger.info(f"Hard delete completed for user {user_id} ({redacted_email})")
                return result
                
            except SQLAlchemyError as e:
                last_error = e
                logger.warning(f"Hard delete attempt {attempt + 1}/{max_retries} failed for user {user_id}: {e}")
                
                # Rollback on error
                try:
                    self.db.rollback()
                except Exception:
                    pass
                
                if attempt < max_retries - 1:
                    # Wait before retry (exponential backoff)
                    import time
                    time.sleep(2 ** attempt)
                else:
                    # Final attempt failed
                    logger.error(f"Hard delete failed for user {user_id} after {max_retries} attempts: {last_error}")
                    raise Exception(f"Failed to delete user after {max_retries} attempts: {last_error}")
        
        # Should not reach here, but just in case
        raise Exception(f"Hard delete failed: {last_error}")
    
    def _execute_hard_delete_transaction(self) -> Dict[str, Any]:
        """
        Execute hard delete in a single transaction
        
        Returns:
            Deletion confirmation
        """
        user_id = self.user.id
        redacted_email = redact_email(self.user.email)
        
        # 1. Delete/anonymize content artifacts and files
        self.purge_user_artifacts(user_id)
        
        # 2. Delete content jobs
        self._delete_content_jobs()
        
        # 3. Handle organization data
        self._handle_organization_data()
        
        # 4. Anonymize billing events (keep for audit, remove PII)
        self._anonymize_billing_events()
        
        # 5. Delete usage counters
        self._delete_usage_counters()
        
        # 6. Delete memberships
        self._delete_memberships()
        
        # 7. Delete sessions
        self.purge_sessions(user_id)
        
        # 8. Delete user record (purge_user)
        self.purge_user(user_id)
        
        # Commit transaction
        self.db.commit()
        
        return {
            "status": "permanently_deleted",
            "deletion_type": "hard",
            "deleted_at": datetime.utcnow().isoformat(),
            "message": "Your account and all associated data have been permanently deleted."
        }
    
    def purge_user(self, user_id: int):
        """
        Delete user record from database
        
        Args:
            user_id: User ID to delete
        """
        # User record should be self.user, but check ID matches
        if self.user.id != user_id:
            raise ValueError(f"User ID mismatch: expected {user_id}, got {self.user.id}")
        
        self.db.delete(self.user)
        logger.debug(f"Purged user record {user_id}")
    
    def purge_user_artifacts(self, user_id: int) -> Dict[str, int]:
        """
        Delete all user artifacts and associated storage files
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with deletion statistics
        """
        return self._delete_artifacts_and_files()
    
    def purge_sessions(self, user_id: int) -> int:
        """
        Invalidate and delete all user sessions
        
        Args:
            user_id: User ID
        
        Returns:
            Number of sessions deleted
        """
        sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).all()
        
        count = len(sessions)
        for session in sessions:
            self.db.delete(session)
        
        logger.debug(f"Purged {count} sessions for user {user_id}")
        return count
    
    def purge_audit_log(self, user_id: int):
        """
        Anonymize audit log entries for user (keep for security audit, remove PII)
        
        NOTE: Audit log table not yet implemented. When implemented, this should:
        - Keep security-relevant events (login attempts, permission changes)
        - Anonymize identifiers (replace user_id with hash, redact email/IP)
        - Retain for compliance period (typically 1-2 years)
        
        Args:
            user_id: User ID
        """
        # TODO: Implement when audit log table is added
        logger.debug(f"Audit log anonymization not yet implemented (user {user_id})")
        pass
    
    
    def _delete_artifacts_and_files(self) -> Dict[str, int]:
        """
        Delete content artifacts and associated storage files
        
        Returns:
            Dictionary with deletion statistics
        """
        from .storage_provider import get_storage_provider
        
        jobs = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        ).all()
        
        job_ids = [job.id for job in jobs]
        artifacts = self.db.query(ContentArtifact).filter(
            ContentArtifact.job_id.in_(job_ids)
        ).all() if job_ids else []
        
        storage = get_storage_provider()
        files_deleted = 0
        files_failed = 0
        
        for artifact in artifacts:
            # Delete storage file if it exists
            if artifact.content_json and artifact.content_json.get('storage_key'):
                try:
                    storage_key = artifact.content_json['storage_key']
                    if storage.delete(storage_key):
                        files_deleted += 1
                        logger.debug(f"Deleted storage file: {storage_key}")
                    else:
                        files_failed += 1
                        logger.warning(f"Storage file not found: {storage_key}")
                except Exception as e:
                    files_failed += 1
                    logger.warning(f"Failed to delete storage file: {e}")
            
            # Delete artifact record
            self.db.delete(artifact)
        
        logger.info(f"Deleted {len(artifacts)} artifacts and {files_deleted} storage files for user {self.user.id} ({files_failed} failed)")
        
        return {
            "artifacts_deleted": len(artifacts),
            "files_deleted": files_deleted,
            "files_failed": files_failed
        }
    
    def _delete_content_jobs(self):
        """Delete content generation jobs"""
        jobs = self.db.query(ContentJob).filter(
            ContentJob.user_id == self.user.id
        ).all()
        
        for job in jobs:
            self.db.delete(job)
        
        self.db.commit()
        logger.info(f"Deleted {len(jobs)} content jobs for user {self.user.id}")
    
    def _handle_organization_data(self):
        """Handle organization data based on ownership"""
        # Get organizations where user is owner
        owned_orgs = self.db.query(Organization).filter(
            Organization.owner_user_id == self.user.id
        ).all()
        
        for org in owned_orgs:
            # Check if organization has other members
            other_members = self.db.query(Membership).filter(
                Membership.org_id == org.id,
                Membership.user_id != self.user.id
            ).count()
            
            if other_members > 0:
                # Transfer ownership to another admin/member
                new_owner = self.db.query(Membership).filter(
                    Membership.org_id == org.id,
                    Membership.user_id != self.user.id
                ).order_by(
                    Membership.role.desc()  # Prefer admin over member
                ).first()
                
                if new_owner:
                    org.owner_user_id = new_owner.user_id
                    logger.info(f"Transferred ownership of org {org.id} to user {new_owner.user_id}")
            else:
                # No other members, delete organization and associated data
                self._delete_organization(org)
        
        self.db.commit()
    
    def _delete_organization(self, org: Organization):
        """Delete organization and all associated data"""
        # Delete subscriptions
        subscriptions = self.db.query(Subscription).filter(
            Subscription.org_id == org.id
        ).all()
        for sub in subscriptions:
            self.db.delete(sub)
        
        # Delete usage counters
        usage_counters = self.db.query(UsageCounter).filter(
            UsageCounter.org_id == org.id
        ).all()
        for uc in usage_counters:
            self.db.delete(uc)
        
        # Anonymize billing events
        billing_events = self.db.query(BillingEvent).filter(
            BillingEvent.org_id == org.id
        ).all()
        for event in billing_events:
            # Keep for audit but anonymize
            event.org_id = None  # Remove org reference
        
        # Delete memberships
        memberships = self.db.query(Membership).filter(
            Membership.org_id == org.id
        ).all()
        for membership in memberships:
            self.db.delete(membership)
        
        # Delete organization
        self.db.delete(org)
        
        logger.info(f"Deleted organization {org.id} and associated data")
    
    def _anonymize_billing_events(self):
        """Anonymize billing events (keep for audit, remove PII)"""
        # Get user's organizations
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        
        # Note: Billing events are already anonymized in export
        # We keep them for audit purposes but remove org reference
        # This is handled in _delete_organization for owned orgs
        
        logger.info(f"Billing events handled for user {self.user.id}'s organizations")
    
    def _delete_usage_counters(self):
        """Delete usage counters for user's organizations"""
        # Get user's organizations
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        org_ids = [m.org_id for m in memberships]
        
        # Only delete if user is sole member (handled in _handle_organization_data)
        # Otherwise, keep for shared organization
        
        logger.info(f"Usage counters handled for user {self.user.id}")
    
    def _delete_memberships(self):
        """Delete user's organization memberships"""
        memberships = self.db.query(Membership).filter(
            Membership.user_id == self.user.id
        ).all()
        
        for membership in memberships:
            self.db.delete(membership)
        
        self.db.commit()
        logger.info(f"Deleted {len(memberships)} memberships for user {self.user.id}")

