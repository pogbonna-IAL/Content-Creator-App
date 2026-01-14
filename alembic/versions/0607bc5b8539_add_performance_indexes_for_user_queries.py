"""add performance indexes for user queries

Revision ID: 0607bc5b8539
Revises: 0607bc5b8538
Create Date: 2026-01-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0607bc5b8539'
down_revision: Union[str, Sequence[str], None] = '0607bc5b8538'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add performance indexes for user-centric queries
    
    This migration adds indexes that weren't covered by previous migrations:
    1. content_jobs(user_id) - for user's job history
    2. content_jobs(user_id, created_at DESC) - for paginated job listing
    3. sessions(user_id) - for session cleanup and user session queries
    4. organizations(owner_id) - for finding organizations owned by a user
    5. content_artifacts(created_at DESC) - for recent artifacts queries
    
    Note: Many other indexes already exist from previous migrations:
    - users(email) unique - migration 0607bc5b8535
    - memberships(org_id, user_id) - migration 0607bc5b8537
    - subscriptions(org_id, status) - migration 0607bc5b8537
    - content_jobs(org_id, created_at DESC) - migration 0607bc5b8537
    - content_jobs(status) - migration 0607bc5b8537
    - content_artifacts(job_id, type) - model definition
    - billing_events(provider, provider_event_id) unique - migration 0607bc5b8537
    """
    
    # content_jobs(user_id) - for filtering jobs by user
    # This is especially useful for user-specific queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_content_jobs_user_id
        ON content_jobs(user_id)
    """)
    
    # content_jobs(user_id, created_at DESC) - composite for user's job history
    # Optimizes queries like: SELECT * FROM content_jobs WHERE user_id = X ORDER BY created_at DESC LIMIT 50
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_content_jobs_user_created_desc
        ON content_jobs(user_id, created_at DESC)
    """)
    
    # sessions(user_id) - for user session queries and cleanup
    # Optimizes: SELECT * FROM sessions WHERE user_id = X
    # And: DELETE FROM sessions WHERE user_id = X (GDPR deletion)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id
        ON sessions(user_id)
    """)
    
    # organizations(owner_id) - for finding organizations owned by a user
    # Optimizes: SELECT * FROM organizations WHERE owner_id = X
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_organizations_owner_id
        ON organizations(owner_id)
    """)
    
    # content_artifacts(created_at DESC) - for recent artifacts queries
    # Optimizes: SELECT * FROM content_artifacts ORDER BY created_at DESC LIMIT 100
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_content_artifacts_created_desc
        ON content_artifacts(created_at DESC)
    """)
    
    # users(deleted_at) - already added in migration 0607bc5b8538
    # This is useful for GDPR cleanup queries: WHERE deleted_at IS NOT NULL AND deleted_at < X
    # No action needed here, just documenting


def downgrade() -> None:
    """Remove performance indexes for user queries."""
    
    op.execute("DROP INDEX IF EXISTS idx_content_artifacts_created_desc")
    op.execute("DROP INDEX IF EXISTS idx_organizations_owner_id")
    op.execute("DROP INDEX IF EXISTS idx_sessions_user_id")
    op.execute("DROP INDEX IF EXISTS idx_content_jobs_user_created_desc")
    op.execute("DROP INDEX IF EXISTS idx_content_jobs_user_id")

