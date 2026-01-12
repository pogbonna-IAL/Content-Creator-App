#!/usr/bin/env python
"""
Database seeding script
Populates the database with initial data for development/testing
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from content_creation_crew.database import (
    SessionLocal,
    User,
    Organization,
    Membership,
    Subscription,
    MembershipRole,
    SubscriptionPlan,
    SubscriptionStatus,
)
# Import enums if not available from database module
try:
    from content_creation_crew.db.models.organization import MembershipRole
except ImportError:
    pass
try:
    from content_creation_crew.db.models.subscription import SubscriptionPlan, SubscriptionStatus
except ImportError:
    pass
from content_creation_crew.auth import get_password_hash
from datetime import datetime, timedelta

def seed_database():
    """Seed database with initial data"""
    db = SessionLocal()
    
    try:
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Database already contains {existing_users} users. Skipping seed.")
            return
        
        print("Seeding database with initial data...")
        
        # Create a test user
        test_user = User(
            email="test@example.com",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            is_active=True,
            is_verified=True,
            auth_provider="email"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        # Create an organization for the test user
        test_org = Organization(
            name="Test Organization",
            owner_user_id=test_user.id
        )
        db.add(test_org)
        db.commit()
        db.refresh(test_org)
        
        # Create membership (user is owner of org)
        membership = Membership(
            org_id=test_org.id,
            user_id=test_user.id,
            role=MembershipRole.OWNER.value
        )
        db.add(membership)
        db.commit()
        
        # Create a free tier subscription for the organization
        subscription = Subscription(
            org_id=test_org.id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.add(subscription)
        db.commit()
        
        print("✓ Database seeded successfully!")
        print(f"  Created test user: test@example.com / testpassword123")
        print(f"  Created organization: {test_org.name}")
        print(f"  Created membership: {membership.role} role")
        print(f"  Created subscription: {subscription.plan} plan")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
