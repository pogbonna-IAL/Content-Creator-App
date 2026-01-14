#!/usr/bin/env python3
"""
Test script for retention notifications
Simulates notification job and displays results
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_data(db: Session):
    """Create test data for notification simulation"""
    from src.content_creation_crew.database import (
        User, Organization, OrganizationMember, Subscription,
        ContentJob, ContentArtifact
    )
    from src.content_creation_crew.auth import get_password_hash
    
    logger.info("Creating test data...")
    
    # Create test organization
    org = Organization(
        name="Test Notification Org",
        created_at=datetime.utcnow()
    )
    db.add(org)
    db.flush()
    
    # Create test user
    user = User(
        email="test-notifications@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        email_verified=True,  # Important: must be verified
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.flush()
    
    # Add user to organization
    member = OrganizationMember(
        user_id=user.id,
        organization_id=org.id,
        role="owner"
    )
    db.add(member)
    
    # Create free plan subscription (30 days retention)
    subscription = Subscription(
        organization_id=org.id,
        plan="free",
        status="active",
        created_at=datetime.utcnow()
    )
    db.add(subscription)
    db.flush()
    
    # Create test artifacts at various ages
    artifacts_config = [
        {"days_old": 29, "type": "video", "topic": "Expiring Today"},
        {"days_old": 28, "type": "audio", "topic": "Expiring Tomorrow"},
        {"days_old": 25, "type": "video", "topic": "Expiring in 5 Days"},
        {"days_old": 24, "type": "blog", "topic": "Expiring in 6 Days"},
        {"days_old": 23, "type": "image", "topic": "Expiring in 7 Days (Notification Threshold)"},
        {"days_old": 15, "type": "video", "topic": "Still Fresh - No Notification"},
        {"days_old": 5, "type": "audio", "topic": "Very Fresh - No Notification"},
    ]
    
    for config in artifacts_config:
        created_at = datetime.utcnow() - timedelta(days=config["days_old"])
        
        # Create job
        job = ContentJob(
            user_id=user.id,
            organization_id=org.id,
            topic=config["topic"],
            content_types=[config["type"]],
            status="completed",
            created_at=created_at
        )
        db.add(job)
        db.flush()
        
        # Create artifact
        artifact = ContentArtifact(
            job_id=job.id,
            artifact_type=config["type"],
            file_path=f"/fake/path/{config['type']}_{job.id}.mp4",
            file_size=1024 * 1024,  # 1MB
            created_at=created_at
        )
        db.add(artifact)
    
    db.commit()
    
    logger.info(f"✓ Created test organization (ID: {org.id})")
    logger.info(f"✓ Created test user: {user.email}")
    logger.info(f"✓ Created {len(artifacts_config)} test artifacts")
    
    return org.id, user.email


def cleanup_test_data(db: Session, org_id: int):
    """Clean up test data"""
    from src.content_creation_crew.database import (
        Organization, User, OrganizationMember,
        Subscription, ContentJob, ContentArtifact
    )
    
    logger.info("Cleaning up test data...")
    
    try:
        # Delete artifacts
        artifacts = db.query(ContentArtifact).join(ContentJob).filter(
            ContentJob.organization_id == org_id
        ).all()
        for artifact in artifacts:
            db.delete(artifact)
        
        # Delete jobs
        jobs = db.query(ContentJob).filter(
            ContentJob.organization_id == org_id
        ).all()
        for job in jobs:
            db.delete(job)
        
        # Delete subscriptions
        subscriptions = db.query(Subscription).filter(
            Subscription.organization_id == org_id
        ).all()
        for sub in subscriptions:
            db.delete(sub)
        
        # Delete members
        members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id
        ).all()
        for member in members:
            # Delete user
            user = db.query(User).get(member.user_id)
            if user:
                db.delete(user)
            db.delete(member)
        
        # Delete organization
        org = db.query(Organization).get(org_id)
        if org:
            db.delete(org)
        
        db.commit()
        logger.info("✓ Cleanup complete")
    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()


def test_notifications(dry_run: bool = True, create_data: bool = True):
    """
    Test retention notifications
    
    Args:
        dry_run: If True, don't send actual emails
        create_data: If True, create test data first
    """
    from src.content_creation_crew.db.engine import SessionLocal
    from src.content_creation_crew.services.retention_notification_service import (
        get_retention_notification_service
    )
    
    logger.info("=" * 80)
    logger.info("RETENTION NOTIFICATION TEST")
    logger.info("=" * 80)
    logger.info(f"Dry Run: {dry_run}")
    logger.info(f"Create Test Data: {create_data}")
    logger.info("=" * 80)
    logger.info("")
    
    db = SessionLocal()
    org_id = None
    
    try:
        # Create test data if requested
        if create_data:
            org_id, user_email = create_test_data(db)
            logger.info("")
        
        # Get notification service
        notification_service = get_retention_notification_service(db, dry_run=dry_run)
        
        logger.info("Running notification job...")
        logger.info("")
        
        # Run notifications
        stats = notification_service.send_notifications_all_organizations()
        
        # Display results
        logger.info("=" * 80)
        logger.info("NOTIFICATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"Organizations Processed: {stats['total_orgs']}")
        logger.info(f"Users Notified: {stats['total_users_notified']}")
        logger.info(f"Users Failed: {stats['total_users_failed']}")
        logger.info(f"Total Artifacts: {stats['total_artifacts']}")
        logger.info(f"Dry Run: {stats['dry_run']}")
        logger.info("=" * 80)
        
        # Display per-org stats
        if stats['org_stats']:
            logger.info("")
            logger.info("PER-ORGANIZATION BREAKDOWN:")
            logger.info("-" * 80)
            for org_stats in stats['org_stats']:
                if org_stats['users_notified'] > 0 or org_stats['total_artifacts'] > 0:
                    logger.info(f"Org {org_stats['org_id']} ({org_stats['plan'].upper()}):")
                    logger.info(f"  Users Notified: {org_stats['users_notified']}")
                    logger.info(f"  Users Failed: {org_stats['users_failed']}")
                    logger.info(f"  Artifacts: {org_stats['total_artifacts']}")
                    logger.info("")
        
        # Summary
        logger.info("")
        if dry_run:
            logger.info("✓ TEST COMPLETE (Dry Run - No Emails Sent)")
        else:
            logger.info("✓ TEST COMPLETE (Emails Sent)")
        
        if stats['total_users_notified'] > 0:
            logger.info(f"  {stats['total_users_notified']} user(s) would receive notifications")
            logger.info(f"  {stats['total_artifacts']} artifact(s) in notifications")
        else:
            logger.info("  No users needed notifications")
        
        logger.info("")
        
        return stats
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return None
    
    finally:
        # Clean up test data if created
        if create_data and org_id:
            logger.info("")
            cleanup_test_data(db, org_id)
        
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test retention notification system"
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Send actual emails (default: dry-run mode)'
    )
    parser.add_argument(
        '--no-create-data',
        action='store_true',
        help='Skip test data creation (use existing data)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run test
    dry_run = not args.live
    create_data = not args.no_create_data
    
    if args.live:
        logger.warning("⚠️  LIVE MODE: Actual emails will be sent!")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Test cancelled")
            return
    
    test_notifications(dry_run=dry_run, create_data=create_data)


if __name__ == '__main__':
    main()

