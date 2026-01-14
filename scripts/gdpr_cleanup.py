#!/usr/bin/env python
"""
GDPR Cleanup Script - Automated Hard Delete
Processes soft-deleted accounts past the grace period

Usage:
    python scripts/gdpr_cleanup.py [--dry-run]

Schedule:
    Run daily via cron/scheduler:
    0 2 * * * cd /app && python scripts/gdpr_cleanup.py >> /var/log/gdpr_cleanup.log 2>&1
"""
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from content_creation_crew.database import User
from content_creation_crew.db.engine import SessionLocal
from content_creation_crew.services.gdpr_deletion_service import GDPRDeletionService
from content_creation_crew.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_deleted_accounts(dry_run: bool = False) -> dict:
    """
    Find and hard delete accounts past the grace period
    
    Args:
        dry_run: If True, only report what would be deleted
    
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "start_time": datetime.utcnow().isoformat(),
        "accounts_found": 0,
        "accounts_deleted": 0,
        "accounts_failed": 0,
        "errors": []
    }
    
    db = SessionLocal()
    
    try:
        # Calculate cutoff date
        grace_period_days = config.GDPR_DELETION_GRACE_DAYS
        cutoff_date = datetime.utcnow() - timedelta(days=grace_period_days)
        
        logger.info(f"Starting GDPR cleanup (grace period: {grace_period_days} days, cutoff: {cutoff_date})")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        
        # Find soft-deleted accounts past grace period
        deleted_users = db.query(User).filter(
            User.deleted_at != None,
            User.deleted_at <= cutoff_date,
            User.is_active == False
        ).all()
        
        stats["accounts_found"] = len(deleted_users)
        logger.info(f"Found {len(deleted_users)} accounts eligible for hard delete")
        
        # Process each account
        for user in deleted_users:
            try:
                logger.info(f"Processing user {user.id} (email: {user.email}, deleted_at: {user.deleted_at})")
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete user {user.id}")
                    stats["accounts_deleted"] += 1
                else:
                    # Execute hard delete
                    deletion_service = GDPRDeletionService(db, user)
                    result = deletion_service.hard_delete()
                    
                    stats["accounts_deleted"] += 1
                    logger.info(f"Successfully deleted user {user.id}")
                
            except Exception as e:
                error_msg = f"Failed to delete user {user.id}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                stats["accounts_failed"] += 1
                stats["errors"].append({
                    "user_id": user.id,
                    "email": user.email,
                    "error": str(e)
                })
        
        stats["end_time"] = datetime.utcnow().isoformat()
        logger.info(f"GDPR cleanup completed: {stats['accounts_deleted']} deleted, {stats['accounts_failed']} failed")
        
        return stats
        
    except Exception as e:
        logger.error(f"Fatal error during GDPR cleanup: {e}", exc_info=True)
        stats["errors"].append({"fatal_error": str(e)})
        return stats
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GDPR Cleanup - Automated Hard Delete")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (report only, no deletions)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("GDPR CLEANUP SCRIPT")
    logger.info("=" * 60)
    
    # Run cleanup
    stats = cleanup_deleted_accounts(dry_run=args.dry_run)
    
    # Print summary
    logger.info("=" * 60)
    logger.info("CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Accounts found: {stats['accounts_found']}")
    logger.info(f"Accounts deleted: {stats['accounts_deleted']}")
    logger.info(f"Accounts failed: {stats['accounts_failed']}")
    
    if stats['errors']:
        logger.error(f"Errors encountered: {len(stats['errors'])}")
        for error in stats['errors']:
            logger.error(f"  - {error}")
    
    logger.info("=" * 60)
    
    # Exit with error code if any failures
    if stats['accounts_failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

