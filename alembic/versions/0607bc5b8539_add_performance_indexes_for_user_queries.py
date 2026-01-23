"""add performance indexes for user queries

Revision ID: 0607bc5b8539
Revises: 0607bc5b8538
Create Date: 2026-01-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


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
    
    # Get list of existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Ensure organizations table exists (required for foreign keys)
    if 'organizations' not in tables:
        op.create_table(
            'organizations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('owner_user_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
        op.create_index(op.f('ix_organizations_name'), 'organizations', ['name'], unique=False)
        op.create_index(op.f('ix_organizations_owner_user_id'), 'organizations', ['owner_user_id'], unique=False)
        tables.append('organizations')
    
    # Ensure content_jobs table exists
    if 'content_jobs' not in tables:
        op.create_table(
            'content_jobs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('org_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('topic', sa.String(), nullable=False),
            sa.Column('formats_requested', sa.JSON(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('idempotency_key', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_content_jobs_id'), 'content_jobs', ['id'], unique=False)
        op.create_index(op.f('ix_content_jobs_org_id'), 'content_jobs', ['org_id'], unique=False)
        op.create_index(op.f('ix_content_jobs_status'), 'content_jobs', ['status'], unique=False)
        op.create_index(op.f('ix_content_jobs_user_id'), 'content_jobs', ['user_id'], unique=False)
        op.create_index(op.f('ix_content_jobs_created_at'), 'content_jobs', ['created_at'], unique=False)
        op.create_index('ix_content_jobs_idempotency_key', 'content_jobs', ['idempotency_key'], unique=True)
        op.create_index('idx_content_jobs_status_created', 'content_jobs', ['status', 'created_at'], unique=False)
        tables.append('content_jobs')
    
    # Ensure content_artifacts table exists
    if 'content_artifacts' not in tables:
        # Check if JSONB is available (PostgreSQL)
        from sqlalchemy.dialects import postgresql
        jsonb_type = postgresql.JSONB if hasattr(postgresql, 'JSONB') else sa.JSON
        
        op.create_table(
            'content_artifacts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(), nullable=False),
            sa.Column('content_json', jsonb_type(), nullable=True),
            sa.Column('content_text', sa.Text(), nullable=True),
            sa.Column('prompt_version', sa.String(), nullable=True),
            sa.Column('model_used', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['job_id'], ['content_jobs.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_content_artifacts_id'), 'content_artifacts', ['id'], unique=False)
        op.create_index(op.f('ix_content_artifacts_job_id'), 'content_artifacts', ['job_id'], unique=False)
        op.create_index(op.f('ix_content_artifacts_type'), 'content_artifacts', ['type'], unique=False)
        op.create_index(op.f('ix_content_artifacts_created_at'), 'content_artifacts', ['created_at'], unique=False)
        op.create_index('idx_content_artifacts_job_type', 'content_artifacts', ['job_id', 'type'], unique=False)
        tables.append('content_artifacts')
    
    # content_jobs(user_id) - for filtering jobs by user
    # This is especially useful for user-specific queries
    if 'content_jobs' in tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_jobs_user_id
            ON content_jobs(user_id)
        """)
    
    # content_jobs(user_id, created_at DESC) - composite for user's job history
    # Optimizes queries like: SELECT * FROM content_jobs WHERE user_id = X ORDER BY created_at DESC LIMIT 50
    if 'content_jobs' in tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_jobs_user_created_desc
            ON content_jobs(user_id, created_at DESC)
        """)
    
    # sessions(user_id) - for user session queries and cleanup
    # Optimizes: SELECT * FROM sessions WHERE user_id = X
    # And: DELETE FROM sessions WHERE user_id = X (GDPR deletion)
    if 'sessions' in tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id
            ON sessions(user_id)
        """)
    
    # organizations(owner_user_id) - for finding organizations owned by a user
    # Optimizes: SELECT * FROM organizations WHERE owner_user_id = X
    if 'organizations' in tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_organizations_owner_user_id
            ON organizations(owner_user_id)
        """)
    
    # content_artifacts(created_at DESC) - for recent artifacts queries
    # Optimizes: SELECT * FROM content_artifacts ORDER BY created_at DESC LIMIT 100
    if 'content_artifacts' in tables:
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

