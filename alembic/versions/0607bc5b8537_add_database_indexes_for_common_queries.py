"""add database indexes for common queries

Revision ID: 0607bc5b8537
Revises: 0607bc5b8536
Create Date: 2026-01-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0607bc5b8537'
down_revision: Union[str, Sequence[str], None] = '0607bc5b8536'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for common queries to improve performance."""
    
    # Get list of existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Note: users(email) already has unique index from initial migration
    # Verify it exists, but don't recreate if it does
    
    # Ensure memberships table exists (it should be created in an earlier migration, but handle missing case)
    if 'memberships' not in tables:
        # Create memberships table if it doesn't exist
        # Ensure organizations table exists first
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
        
        # Create memberships table
        op.create_table(
            'memberships',
            sa.Column('org_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('role', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('org_id', 'user_id')
        )
        op.create_index(op.f('ix_memberships_org_id'), 'memberships', ['org_id'], unique=False)
        op.create_index(op.f('ix_memberships_user_id'), 'memberships', ['user_id'], unique=False)
        tables.append('memberships')  # Update tables list
    
    # memberships(org_id, user_id) - composite index for membership lookups
    # Note: These are primary keys, but composite index helps with queries filtering by both
    if 'memberships' in tables:
        # Check if index already exists
        indexes = [idx['name'] for idx in inspector.get_indexes('memberships')]
        if 'idx_memberships_org_user' not in indexes:
            op.create_index(
                'idx_memberships_org_user',
                'memberships',
                ['org_id', 'user_id'],
                unique=False
            )
    
    # subscriptions(org_id, status) - composite index for filtering subscriptions by org and status
    if 'subscriptions' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('subscriptions')]
        if 'idx_subscriptions_org_status' not in indexes:
            op.create_index(
                'idx_subscriptions_org_status',
                'subscriptions',
                ['org_id', 'status'],
                unique=False
            )
    
    # usage_counters(org_id, period_month) - composite index for usage lookups
    # Note: Already has unique constraint, but explicit index helps with queries
    if 'usage_counters' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('usage_counters')]
        if 'idx_usage_counters_org_period' not in indexes:
            op.create_index(
                'idx_usage_counters_org_period',
                'usage_counters',
                ['org_id', 'period_month'],
                unique=False
            )
    
    # content_jobs(org_id, created_at desc) - composite index for listing jobs by org, newest first
    # Use raw SQL for DESC ordering as Alembic doesn't support DESC in column list directly
    if 'content_jobs' in tables:
        # Check if index exists
        result = conn.execute(sa.text("""
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'content_jobs' 
            AND indexname = 'idx_content_jobs_org_created_desc'
        """))
        if result.fetchone() is None:
            op.execute("""
                CREATE INDEX idx_content_jobs_org_created_desc 
                ON content_jobs(org_id, created_at DESC)
            """)
    
    # content_jobs(status) - index for filtering by status
    # Note: Already has index from model definition, but ensure it exists
    # Check if index exists first (PostgreSQL specific)
    if 'content_jobs' in tables:
        op.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_jobs_status 
            ON content_jobs(status)
        """)
    
    # content_artifacts(job_id, type) - composite index for artifact lookups
    # Note: Already has index from model definition (idx_content_artifacts_job_type)
    # Verify it exists, but don't recreate if it does
    
    # billing_events(provider, provider_event_id) unique - composite unique index for webhook deduplication
    # Note: provider_event_id is already unique globally, but composite unique constraint ensures uniqueness per provider
    # This is more specific and helps with queries filtering by provider
    # Check if composite constraint already exists
    if 'billing_events' in tables:
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'uq_billing_events_provider_event_id_composite'
                ) THEN
                    ALTER TABLE billing_events 
                    ADD CONSTRAINT uq_billing_events_provider_event_id_composite 
                    UNIQUE (provider, provider_event_id);
                END IF;
            END $$;
        """)


def downgrade() -> None:
    """Remove indexes added for common queries."""
    
    # Drop unique constraint (use IF EXISTS for safety)
    op.execute("""
        ALTER TABLE billing_events 
        DROP CONSTRAINT IF EXISTS uq_billing_events_provider_event_id_composite;
    """)
    
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_content_jobs_status;")
    op.execute("DROP INDEX IF EXISTS idx_content_jobs_org_created_desc;")
    op.drop_index('idx_usage_counters_org_period', table_name='usage_counters', if_exists=True)
    op.drop_index('idx_subscriptions_org_status', table_name='subscriptions', if_exists=True)
    op.drop_index('idx_memberships_org_user', table_name='memberships', if_exists=True)

