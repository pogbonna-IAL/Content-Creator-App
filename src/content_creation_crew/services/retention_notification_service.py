"""
Retention Notification Service (M1 Enhancement)
Send email notifications before artifacts are deleted due to retention policy
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RetentionNotificationService:
    """
    Sends email notifications to users before their artifacts are deleted
    
    Features:
    - Configurable notification window (default: 7 days before deletion)
    - Batched notifications to avoid email spam
    - Tracks sent notifications to avoid duplicates
    - Groups artifacts by user for single email
    - Respects user email preferences
    - Dry-run mode support
    """
    
    def __init__(self, db: Session, dry_run: bool = False):
        """
        Initialize notification service
        
        Args:
            db: Database session
            dry_run: If True, log actions without sending emails
        """
        self.db = db
        self.dry_run = dry_run
        
        # Load configuration
        from ..config import config
        
        self.notify_days_before = config.RETENTION_NOTIFY_DAYS_BEFORE
        self.notify_enabled = config.RETENTION_NOTIFY_ENABLED
        self.batch_size = config.RETENTION_NOTIFY_BATCH_SIZE
        
        logger.info(
            f"RetentionNotificationService initialized "
            f"(dry_run={dry_run}, notify_days_before={self.notify_days_before}, "
            f"enabled={self.notify_enabled})"
        )
    
    def compute_notification_date(self, plan: str) -> Optional[datetime]:
        """
        Compute date when notifications should be sent
        
        Args:
            plan: Subscription plan
        
        Returns:
            Date when to notify (artifacts expiring after this date need notification)
            None if plan has unlimited retention
        """
        from .artifact_retention_service import ArtifactRetentionService
        
        retention_service = ArtifactRetentionService(self.db, dry_run=self.dry_run)
        retention_days = retention_service.compute_retention_days(plan)
        
        if retention_days == -1:
            return None  # Unlimited retention, no notifications
        
        # Notify X days before deletion
        # Example: 30-day retention, 7-day notice = notify for artifacts 23+ days old
        notification_threshold = retention_days - self.notify_days_before
        
        if notification_threshold <= 0:
            # Retention period shorter than notification window
            # Notify immediately after creation
            notification_threshold = 0
        
        return datetime.utcnow() - timedelta(days=notification_threshold)
    
    def check_already_notified(self, user_id: int, artifact_id: int, notification_date: datetime.date) -> bool:
        """
        Check if notification was already sent for this artifact today
        
        Args:
            user_id: User ID
            artifact_id: Artifact ID
            notification_date: Notification date
        
        Returns:
            True if already notified
        """
        from ..database import RetentionNotification
        
        try:
            existing = self.db.query(RetentionNotification).filter(
                RetentionNotification.user_id == user_id,
                RetentionNotification.artifact_id == artifact_id,
                RetentionNotification.notification_date == notification_date
            ).first()
            
            return existing is not None
        
        except Exception as e:
            logger.error(f"Error checking notification status: {e}", exc_info=True)
            return False  # Assume not notified on error
    
    def record_notification(
        self,
        user_id: int,
        org_id: int,
        artifact_id: int,
        artifact_type: str,
        artifact_topic: str,
        expiration_date: datetime.date,
        email_sent: bool = False,
        failure_reason: str = None
    ) -> None:
        """
        Record notification attempt in database
        
        Args:
            user_id: User ID
            org_id: Organization ID
            artifact_id: Artifact ID
            artifact_type: Artifact type
            artifact_topic: Artifact topic
            expiration_date: Expected deletion date
            email_sent: Whether email was sent successfully
            failure_reason: Reason for failure (if any)
        """
        from ..database import RetentionNotification
        
        try:
            notification = RetentionNotification(
                user_id=user_id,
                organization_id=org_id,
                artifact_id=artifact_id,
                notification_date=datetime.utcnow().date(),
                expiration_date=expiration_date,
                artifact_type=artifact_type,
                artifact_topic=artifact_topic[:500] if artifact_topic else None,
                email_sent=email_sent,
                email_sent_at=datetime.utcnow() if email_sent else None,
                email_failed=not email_sent,
                failure_reason=failure_reason[:500] if failure_reason else None,
                created_at=datetime.utcnow()
            )
            
            self.db.add(notification)
            
            if not self.dry_run:
                self.db.commit()
                logger.debug(
                    f"Recorded notification for artifact {artifact_id} "
                    f"(user={user_id}, sent={email_sent})"
                )
            else:
                self.db.rollback()
                logger.debug(f"[DRY RUN] Would record notification for artifact {artifact_id}")
        
        except Exception as e:
            logger.error(f"Error recording notification: {e}", exc_info=True)
            self.db.rollback()
    
    def find_artifacts_needing_notification(
        self,
        org_id: int,
        plan: str
    ) -> List[Dict[str, Any]]:
        """
        Find artifacts that need expiration notifications
        Excludes artifacts already notified today
        
        Args:
            org_id: Organization ID
            plan: Subscription plan
        
        Returns:
            List of artifact info dicts grouped by user
        """
        from ..database import ContentArtifact, ContentJob, User, OrganizationMember, RetentionNotification, Membership
        from .artifact_retention_service import ArtifactRetentionService
        from sqlalchemy import and_
        
        notification_date = self.compute_notification_date(plan)
        
        if not notification_date:
            return []  # No notifications for unlimited retention
        
        # Calculate deletion date range
        retention_service = ArtifactRetentionService(self.db, dry_run=self.dry_run)
        deletion_cutoff = retention_service.compute_cutoff_date(plan)
        
        if not deletion_cutoff:
            return []
        
        today = datetime.utcnow().date()
        
        try:
            # Find artifacts expiring soon that haven't been notified today
            # Use LEFT JOIN to exclude artifacts with notifications today
            # Note: ContentJob, Membership, and Subscription models use 'org_id' not 'organization_id'
            artifacts = self.db.query(
                ContentArtifact.id,
                ContentArtifact.artifact_type,
                ContentArtifact.created_at,
                ContentJob.topic,
                ContentJob.org_id.label('organization_id'),  # Alias org_id as organization_id for compatibility
                User.id.label('user_id'),
                User.email
            ).join(
                ContentJob, ContentArtifact.job_id == ContentJob.id
            ).join(
                User, ContentJob.user_id == User.id
            ).join(
                Membership,
                and_(
                    User.id == Membership.user_id,
                    ContentJob.org_id == Membership.org_id  # Use org_id for both
                )
            ).outerjoin(
                RetentionNotification,
                and_(
                    RetentionNotification.artifact_id == ContentArtifact.id,
                    RetentionNotification.user_id == User.id,
                    RetentionNotification.notification_date == today
                )
            ).filter(
                ContentJob.org_id == org_id,  # Use org_id instead of organization_id
                ContentArtifact.created_at < notification_date,
                ContentArtifact.created_at >= deletion_cutoff,  # Not yet expired
                User.email_verified == True,  # Only notify verified emails
                RetentionNotification.id == None  # Not notified today
            ).limit(self.batch_size).all()
            
            # Group by user
            user_artifacts = {}
            for artifact in artifacts:
                user_id = artifact.user_id
                if user_id not in user_artifacts:
                    user_artifacts[user_id] = {
                        'user_id': user_id,
                        'email': artifact.email,
                        'org_id': artifact.organization_id,  # This is the aliased org_id
                        'plan': plan,
                        'artifacts': []
                    }
                
                # Calculate days until deletion
                days_until_deletion = (deletion_cutoff - artifact.created_at).days
                
                user_artifacts[user_id]['artifacts'].append({
                    'id': artifact.id,
                    'type': artifact.artifact_type,
                    'topic': artifact.topic,
                    'created_at': artifact.created_at,
                    'days_until_deletion': max(0, days_until_deletion),
                    'expiration_date': (artifact.created_at + timedelta(days=retention_service.compute_retention_days(plan))).date()
                })
            
            logger.info(
                f"Found {len(artifacts)} artifacts needing notification for {len(user_artifacts)} users "
                f"(org={org_id}, plan={plan})"
            )
            
            return list(user_artifacts.values())
        
        except Exception as e:
            logger.error(f"Error finding artifacts for notification: {e}", exc_info=True)
            return []
    
    def send_expiration_notification(
        self,
        user_email: str,
        user_artifacts: Dict[str, Any]
    ) -> bool:
        """
        Send expiration notification email to user with HTML formatting
        
        Args:
            user_email: User's email address
            user_artifacts: Dict with user info and artifact list
        
        Returns:
            True if email sent successfully
        """
        from .email_provider import get_email_provider, EmailMessage
        from .email_templates import RetentionNotificationTemplate
        
        try:
            email_provider = get_email_provider()
            
            # Prepare email content
            plan = user_artifacts['plan']
            artifacts = user_artifacts['artifacts']
            total_artifacts = len(artifacts)
            
            # Group by days until deletion
            deletion_groups = {}
            for artifact in artifacts:
                days = artifact['days_until_deletion']
                if days not in deletion_groups:
                    deletion_groups[days] = []
                deletion_groups[days].append(artifact)
            
            # Build subject
            subject = f"⚠️ {total_artifacts} artifact{'s' if total_artifacts != 1 else ''} will be deleted soon"
            
            # Render email templates
            html_body = RetentionNotificationTemplate.render_html(
                plan=plan,
                artifacts=artifacts,
                deletion_groups=deletion_groups
            )
            
            text_body = RetentionNotificationTemplate.render_plain_text(
                plan=plan,
                artifacts=artifacts,
                deletion_groups=deletion_groups
            )
            
            # Create email message
            message = EmailMessage(
                to=user_email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            # Send email
            email_sent = False
            failure_reason = None
            
            try:
                if not self.dry_run:
                    email_sent = email_provider.send(message)
                    if email_sent:
                        logger.info(f"Sent retention notification to {user_email} ({total_artifacts} artifacts)")
                    else:
                        failure_reason = "Email provider returned False"
                        logger.error(f"Email provider failed to send to {user_email}")
                else:
                    email_sent = True  # Consider successful in dry-run
                    logger.info(f"[DRY RUN] Would send retention notification to {user_email} ({total_artifacts} artifacts)")
            
            except Exception as email_error:
                failure_reason = str(email_error)
                logger.error(f"Failed to send email to {user_email}: {email_error}")
            
            # Record notification attempts for all artifacts
            user_id = user_artifacts['user_id']
            org_id = user_artifacts.get('org_id')
            
            for artifact in artifacts:
                self.record_notification(
                    user_id=user_id,
                    org_id=org_id,
                    artifact_id=artifact['id'],
                    artifact_type=artifact['type'],
                    artifact_topic=artifact['topic'],
                    expiration_date=artifact.get('expiration_date', datetime.utcnow().date()),
                    email_sent=email_sent,
                    failure_reason=failure_reason
                )
            
            return email_sent
        
        except Exception as e:
            logger.error(f"Error sending notification to {user_email}: {e}", exc_info=True)
            return False
    
    def send_notifications_for_organization(
        self,
        org_id: int,
        plan: str
    ) -> Dict[str, Any]:
        """
        Send retention notifications for an organization
        
        Args:
            org_id: Organization ID
            plan: Subscription plan
        
        Returns:
            Dict with notification statistics
        """
        stats = {
            "org_id": org_id,
            "plan": plan,
            "users_notified": 0,
            "users_failed": 0,
            "total_artifacts": 0,
            "dry_run": self.dry_run
        }
        
        if not self.notify_enabled:
            logger.info("Retention notifications disabled via config")
            return stats
        
        try:
            # Find artifacts needing notification
            user_artifacts_list = self.find_artifacts_needing_notification(org_id, plan)
            
            if not user_artifacts_list:
                logger.info(f"No artifacts need notification for org {org_id}")
                return stats
            
            # Send notifications
            for user_artifacts in user_artifacts_list:
                user_email = user_artifacts['email']
                artifact_count = len(user_artifacts['artifacts'])
                
                stats["total_artifacts"] += artifact_count
                
                success = self.send_expiration_notification(user_email, user_artifacts)
                
                if success:
                    stats["users_notified"] += 1
                else:
                    stats["users_failed"] += 1
            
            logger.info(
                f"Sent {stats['users_notified']} notifications for org {org_id} "
                f"({stats['total_artifacts']} artifacts)"
            )
            
            return stats
        
        except Exception as e:
            logger.error(f"Error sending notifications for org {org_id}: {e}", exc_info=True)
            return stats
    
    def send_notifications_all_organizations(self) -> Dict[str, Any]:
        """
        Send retention notifications for all organizations
        
        Returns:
            Dict with overall statistics
        """
        from ..database import Organization, Subscription
        
        overall_stats = {
            "total_orgs": 0,
            "total_users_notified": 0,
            "total_users_failed": 0,
            "total_artifacts": 0,
            "dry_run": self.dry_run,
            "org_stats": []
        }
        
        if not self.notify_enabled:
            logger.info("Retention notifications disabled via config")
            return overall_stats
        
        try:
            # Get all organizations
            orgs = self.db.query(Organization).all()
            overall_stats["total_orgs"] = len(orgs)
            
            logger.info(f"Sending retention notifications for {len(orgs)} organizations")
            
            for org in orgs:
                # Get active subscription
                # Note: Subscription model uses 'org_id' not 'organization_id'
                active_sub = self.db.query(Subscription).filter(
                    Subscription.org_id == org.id,
                    Subscription.status == 'active'
                ).first()
                
                plan = active_sub.plan if active_sub else 'free'
                
                # Skip enterprise (unlimited retention)
                if plan.lower() == 'enterprise':
                    continue
                
                # Send notifications for this org
                org_stats = self.send_notifications_for_organization(org.id, plan)
                
                # Aggregate statistics
                overall_stats["total_users_notified"] += org_stats["users_notified"]
                overall_stats["total_users_failed"] += org_stats["users_failed"]
                overall_stats["total_artifacts"] += org_stats["total_artifacts"]
                overall_stats["org_stats"].append(org_stats)
            
            logger.info(
                f"Retention notifications complete: "
                f"{overall_stats['total_users_notified']} users notified, "
                f"{overall_stats['total_artifacts']} artifacts"
            )
            
            return overall_stats
        
        except Exception as e:
            logger.error(f"Error during retention notifications: {e}", exc_info=True)
            return overall_stats


def get_retention_notification_service(db: Session, dry_run: bool = False) -> RetentionNotificationService:
    """
    Get retention notification service instance
    
    Args:
        db: Database session
        dry_run: Enable dry-run mode
    
    Returns:
        RetentionNotificationService instance
    """
    from ..config import config
    
    # Override dry_run with config if retention dry_run is set
    if config.RETENTION_DRY_RUN:
        dry_run = True
        logger.info("RETENTION_DRY_RUN is enabled - notifications will not be sent")
    
    return RetentionNotificationService(db, dry_run=dry_run)

