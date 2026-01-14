"""
Scheduled Jobs Service
Manages background jobs for GDPR cleanup and other periodic tasks
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import config

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """
    Get or create the background scheduler instance
    
    Returns:
        BackgroundScheduler instance
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            job_defaults={
                'coalesce': True,  # Combine missed runs
                'max_instances': 1,  # Only one instance at a time
                'misfire_grace_time': 3600  # 1 hour grace period
            }
        )
    
    return _scheduler


def start_scheduler():
    """
    Start the background scheduler and register all jobs
    """
    scheduler = get_scheduler()
    
    if not scheduler.running:
        # Register dunning processing job (hourly)
        scheduler.add_job(
            func=run_dunning_processing_job,
            trigger=CronTrigger(minute=0),  # Every hour at minute 0
            id='dunning_processing',
            name='Process dunning actions',
            replace_existing=True
        )
        logger.info("Registered dunning processing job (hourly)")
        
        # Register GDPR cleanup job
        scheduler.add_job(
            func=run_gdpr_cleanup_job,
            trigger=CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id='gdpr_cleanup',
            name='GDPR Hard Delete Cleanup',
            replace_existing=True
        )
        logger.info("Registered GDPR cleanup job (daily at 2 AM)")
        
        # Register session cleanup job
        scheduler.add_job(
            func=run_session_cleanup_job,
            trigger=CronTrigger(hour=3, minute=0),  # Daily at 3 AM
            id='session_cleanup',
            name='Expired Session Cleanup',
            replace_existing=True
        )
        logger.info("Registered session cleanup job (daily at 3 AM)")
        
        # Register artifact retention notification job (M1 Enhancement)
        scheduler.add_job(
            func=run_retention_notification_job,
            trigger=CronTrigger(hour=10, minute=0),  # Daily at 10 AM (user-friendly time)
            id='retention_notifications',
            name='Artifact Retention Notifications',
            replace_existing=True
        )
        logger.info("Registered artifact retention notification job (daily at 10 AM)")
        
        # Register artifact retention cleanup job (M1)
        scheduler.add_job(
            func=run_retention_cleanup_job,
            trigger=CronTrigger(hour=4, minute=0),  # Daily at 4 AM
            id='retention_cleanup',
            name='Artifact Retention Cleanup',
            replace_existing=True
        )
        logger.info("Registered artifact retention cleanup job (daily at 4 AM)")
        
        # Start scheduler
        scheduler.start()
        logger.info("Background scheduler started")
    else:
        logger.warning("Scheduler already running")


def stop_scheduler():
    """
    Stop the background scheduler
    """
    scheduler = get_scheduler()
    
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")


def run_gdpr_cleanup_job():
    """
    GDPR cleanup job - runs daily to hard delete accounts past grace period
    
    This function is called by the scheduler and executes the cleanup script logic.
    """
    from sqlalchemy.orm import Session
    from ..database import User
    from ..db.engine import SessionLocal
    from .gdpr_deletion_service import GDPRDeletionService, SOFT_DELETE_GRACE_PERIOD_DAYS, redact_email
    
    logger.info("=" * 60)
    logger.info("Starting scheduled GDPR cleanup job")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=SOFT_DELETE_GRACE_PERIOD_DAYS)
        
        logger.info(f"Grace period: {SOFT_DELETE_GRACE_PERIOD_DAYS} days, cutoff: {cutoff_date}")
        
        # Find soft-deleted accounts past grace period
        deleted_users = db.query(User).filter(
            User.deleted_at != None,
            User.deleted_at <= cutoff_date,
            User.is_active == False
        ).all()
        
        logger.info(f"Found {len(deleted_users)} accounts eligible for hard delete")
        
        # Track statistics
        accounts_deleted = 0
        accounts_failed = 0
        errors = []
        total_bytes_freed = 0
        
        # Process each account
        for user in deleted_users:
            try:
                redacted_email = redact_email(user.email)
                logger.info(f"Processing user {user.id} ({redacted_email}, deleted_at: {user.deleted_at})")
                
                # Execute hard delete
                deletion_service = GDPRDeletionService(db, user)
                result = deletion_service.hard_delete(max_retries=3)
                
                accounts_deleted += 1
                # Track bytes freed if available
                if result and 'bytes_freed' in result:
                    total_bytes_freed += result.get('bytes_freed', 0)
                
                logger.info(f"Successfully deleted user {user.id}")
                
            except Exception as e:
                error_msg = f"Failed to delete user {user.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                accounts_failed += 1
                errors.append({
                    "user_id": user.id,
                    "error": str(e)
                })
        
        # Log summary
        logger.info("=" * 60)
        logger.info("GDPR Cleanup Job Summary")
        logger.info("=" * 60)
        logger.info(f"Accounts found: {len(deleted_users)}")
        logger.info(f"Accounts deleted: {accounts_deleted}")
        logger.info(f"Accounts failed: {accounts_failed}")
        
        if errors:
            logger.error(f"Errors encountered: {len(errors)}")
            for error in errors:
                logger.error(f"  - User {error['user_id']}: {error['error']}")
        
        logger.info("=" * 60)
        
        # Track retention metrics (M7)
        try:
            from .metrics import RetentionMetrics, increment_counter
            
            # Record cleanup run
            RetentionMetrics.record_cleanup_run(
                duration=0,  # Duration tracked at job level
                total_items=accounts_deleted,
                total_bytes=total_bytes_freed
            )
            
            # Record per-plan deletions (future: track by plan)
            if accounts_deleted > 0:
                RetentionMetrics.record_delete("gdpr", accounts_deleted, total_bytes_freed)
            
            # Legacy metrics
            increment_counter("gdpr_cleanup_runs_total", labels={"status": "success" if accounts_failed == 0 else "partial_failure"})
            increment_counter("gdpr_hard_deletes_total", labels={"status": "success"}, value=accounts_deleted)
            increment_counter("gdpr_hard_deletes_total", labels={"status": "failed"}, value=accounts_failed)
        except ImportError:
            pass
        
    except Exception as e:
        logger.error(f"Fatal error during GDPR cleanup job: {e}", exc_info=True)
        
        # Track fatal error metric
        try:
            from .metrics import increment_counter
            increment_counter("gdpr_cleanup_runs_total", labels={"status": "fatal_error"})
        except ImportError:
            pass
        
    finally:
        db.close()
        logger.info("GDPR cleanup job finished")


def run_session_cleanup_job():
    """
    Session cleanup job - runs daily to remove expired sessions
    
    Expired sessions are automatically removed from the database to:
    1. Reduce database size
    2. Improve query performance
    3. Clean up stale authentication data
    
    Note: Token blacklist entries expire automatically via Redis TTL
    """
    from sqlalchemy.orm import Session
    from ..database import Session as UserSession
    from ..db.engine import SessionLocal
    from datetime import datetime, timedelta
    
    logger.info("=" * 60)
    logger.info("Starting scheduled session cleanup job")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Find expired sessions (older than 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        logger.info(f"Cutoff date: {cutoff_date} (7 days ago)")
        
        # Count sessions to delete
        expired_count = db.query(UserSession).filter(
            UserSession.created_at < cutoff_date
        ).count()
        
        logger.info(f"Found {expired_count} expired sessions to delete")
        
        if expired_count > 0:
            # Delete expired sessions
            deleted = db.query(UserSession).filter(
                UserSession.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(f"✓ Deleted {deleted} expired sessions")
        else:
            logger.info("No expired sessions to delete")
        
        # Track metrics
        try:
            from .metrics import increment_counter
            increment_counter("session_cleanup_runs_total", labels={"status": "success"})
            if expired_count > 0:
                increment_counter("sessions_cleaned_total", value=expired_count)
        except ImportError:
            pass
        
    except Exception as e:
        logger.error(f"Session cleanup job failed: {e}", exc_info=True)
        
        try:
            from .metrics import increment_counter
            increment_counter("session_cleanup_runs_total", labels={"status": "failed"})
        except ImportError:
            pass
        
    finally:
        db.close()
        logger.info("Session cleanup job finished")
        logger.info("=" * 60)


def run_retention_cleanup_job():
    """
    Artifact retention cleanup job - runs daily to delete expired artifacts (M1)
    
    Deletes artifacts based on subscription tier retention policy:
    - Free: 30 days
    - Basic: 90 days
    - Pro: 365 days
    - Enterprise: Unlimited (no auto-deletion except GDPR)
    
    Deletion includes both database records and storage files.
    """
    from sqlalchemy.orm import Session
    from ..db.engine import SessionLocal
    from .artifact_retention_service import get_retention_service
    from .audit_log_service import get_audit_log_service
    import time
    
    logger.info("=" * 60)
    logger.info("Starting scheduled artifact retention cleanup job")
    logger.info("=" * 60)
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        # Get retention service
        retention_service = get_retention_service(db, dry_run=False)
        
        # Run cleanup for all organizations
        stats = retention_service.cleanup_all_organizations()
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log summary
        logger.info("=" * 60)
        logger.info("Artifact Retention Cleanup Job Summary")
        logger.info("=" * 60)
        logger.info(f"Organizations processed: {stats['total_orgs']}")
        logger.info(f"Artifacts found: {stats['total_artifacts_found']}")
        logger.info(f"Artifacts deleted: {stats['total_artifacts_deleted']}")
        logger.info(f"Artifacts failed: {stats['total_artifacts_failed']}")
        logger.info(f"Bytes freed: {stats['total_bytes_freed']} ({stats['total_bytes_freed'] / (1024*1024):.2f} MB)")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Dry run: {stats['dry_run']}")
        logger.info("=" * 60)
        
        # Track retention metrics (M7)
        try:
            from .metrics import RetentionMetrics
            
            # Record overall cleanup run
            RetentionMetrics.record_cleanup_run(
                duration=duration,
                total_items=stats['total_artifacts_deleted'],
                total_bytes=stats['total_bytes_freed']
            )
            
            # Record per-plan deletions
            plan_summary = {}
            for org_stats in stats['org_stats']:
                plan = org_stats['plan']
                if plan not in plan_summary:
                    plan_summary[plan] = {'items': 0, 'bytes': 0}
                plan_summary[plan]['items'] += org_stats['artifacts_deleted']
                plan_summary[plan]['bytes'] += org_stats['bytes_freed']
            
            for plan, summary in plan_summary.items():
                if summary['items'] > 0:
                    RetentionMetrics.record_delete(plan, summary['items'], summary['bytes'])
        
        except ImportError:
            pass
        
        # Audit log (only if artifacts were deleted)
        if stats['total_artifacts_deleted'] > 0 and not stats['dry_run']:
            try:
                audit_service = get_audit_log_service(db)
                audit_service.log_action(
                    action_type="ARTIFACT_RETENTION_DELETE",
                    actor_user_id=None,  # System action
                    details={
                        "total_orgs": stats['total_orgs'],
                        "artifacts_deleted": stats['total_artifacts_deleted'],
                        "bytes_freed": stats['total_bytes_freed']
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create audit log entry: {e}")
    
    except Exception as e:
        logger.error(f"Fatal error during retention cleanup job: {e}", exc_info=True)
        
        # Track fatal error metric
        try:
            from .metrics import increment_counter
            increment_counter("retention_cleanup_runs_total", labels={"status": "fatal_error"})
        except ImportError:
            pass
    
    finally:
        db.close()
        logger.info("Artifact retention cleanup job finished")


def run_dunning_processing_job():
    """
    Dunning processing job - runs hourly to process due dunning actions
    
    Handles:
    - Payment retries
    - Email notifications
    - Subscription cancellations
    """
    from ..db.engine import SessionLocal
    from .dunning_service import get_dunning_service
    from .metrics import increment_counter
    
    logger.info("=" * 60)
    logger.info("Starting scheduled dunning processing job")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        dunning_service = get_dunning_service(db)
        
        # Process all due dunning actions
        stats = dunning_service.process_dunning_actions()
        
        logger.info("Dunning processing complete:")
        logger.info(f"  - Processes handled: {stats['processed']}")
        logger.info(f"  - Retries attempted: {stats['retries_attempted']}")
        logger.info(f"  - Retries succeeded: {stats['retries_succeeded']}")
        logger.info(f"  - Retries failed: {stats['retries_failed']}")
        logger.info(f"  - Emails sent: {stats['emails_sent']}")
        logger.info(f"  - Subscriptions cancelled: {stats['subscriptions_cancelled']}")
        
        # Track metrics
        increment_counter("dunning_processing_runs_total", 1)
        increment_counter("dunning_retries_total", stats['retries_attempted'])
        increment_counter("dunning_retries_succeeded_total", stats['retries_succeeded'])
        increment_counter("dunning_emails_sent_total", stats['emails_sent'])
        increment_counter("dunning_cancellations_total", stats['subscriptions_cancelled'])
        
    except Exception as e:
        logger.error(f"Dunning processing job failed: {e}", exc_info=True)
        increment_counter("dunning_processing_errors_total", 1)
    finally:
        db.close()
    
    logger.info("Dunning processing job completed")
    logger.info("=" * 60)


def run_retention_notification_job():
    """
    Artifact retention notification job - runs daily to notify users about upcoming deletions (M1 Enhancement)
    
    Sends email notifications to users X days before their artifacts are deleted,
    giving them time to download content or upgrade their plan.
    """
    from sqlalchemy.orm import Session
    from ..db.engine import SessionLocal
    from .retention_notification_service import get_retention_notification_service
    import time
    
    logger.info("=" * 60)
    logger.info("Starting scheduled artifact retention notification job")
    logger.info("=" * 60)
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        # Get notification service
        notification_service = get_retention_notification_service(db, dry_run=False)
        
        # Send notifications for all organizations
        stats = notification_service.send_notifications_all_organizations()
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log summary
        logger.info("=" * 60)
        logger.info("Artifact Retention Notification Job Summary")
        logger.info("=" * 60)
        logger.info(f"Organizations processed: {stats['total_orgs']}")
        logger.info(f"Users notified: {stats['total_users_notified']}")
        logger.info(f"Users failed: {stats['total_users_failed']}")
        logger.info(f"Total artifacts: {stats['total_artifacts']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Dry run: {stats['dry_run']}")
        logger.info("=" * 60)
        
        # Track metrics
        try:
            from .metrics import increment_counter, observe_histogram
            
            increment_counter(
                "retention_notifications_total", 
                labels={"status": "success"}, 
                value=stats['total_users_notified']
            )
            
            if stats['total_users_failed'] > 0:
                increment_counter(
                    "retention_notifications_total", 
                    labels={"status": "failed"}, 
                    value=stats['total_users_failed']
                )
            
            observe_histogram("retention_notification_seconds", duration)
            
        except ImportError:
            pass
    
    except Exception as e:
        logger.error(f"Fatal error during retention notification job: {e}", exc_info=True)
        
        # Track fatal error metric
        try:
            from .metrics import increment_counter
            increment_counter("retention_notification_runs_total", labels={"status": "fatal_error"})
        except ImportError:
            pass
    
    finally:
        db.close()
        logger.info("Artifact retention notification job finished")


# Export functions
__all__ = [
    'get_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'run_gdpr_cleanup_job',
    'run_session_cleanup_job',
    'run_retention_cleanup_job',
    'run_retention_notification_job'
]

