"""add media generation counters

Revision ID: 0607bc5b8536
Revises: 0607bc5b8535
Create Date: 2026-01-12 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0607bc5b8536'
down_revision = '0607bc5b8535'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if usage_counters table exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'usage_counters' not in tables:
        # Table doesn't exist - create it with all columns
        # First, ensure organizations table exists (required for foreign key)
        if 'organizations' not in tables:
            # Create organizations table first
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
        
        # Create usage_counters table with all columns
        op.create_table(
            'usage_counters',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('org_id', sa.Integer(), nullable=False),
            sa.Column('period_month', sa.String(), nullable=False),
            sa.Column('blog_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('social_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('audio_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('video_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('voiceover_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('video_render_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('org_id', 'period_month', name='uq_usage_counters_org_period')
        )
        op.create_index(op.f('ix_usage_counters_id'), 'usage_counters', ['id'], unique=False)
        op.create_index(op.f('ix_usage_counters_org_id'), 'usage_counters', ['org_id'], unique=False)
        op.create_index(op.f('ix_usage_counters_period_month'), 'usage_counters', ['period_month'], unique=False)
    else:
        # Table exists - just add the new columns
        # Check if columns already exist to make migration idempotent
        columns = [col['name'] for col in inspector.get_columns('usage_counters')]
        
        if 'voiceover_count' not in columns:
            op.add_column('usage_counters', sa.Column('voiceover_count', sa.Integer(), nullable=False, server_default='0'))
        
        if 'video_render_count' not in columns:
            op.add_column('usage_counters', sa.Column('video_render_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Check if table exists
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'usage_counters' in tables:
        # Check if columns exist before dropping
        columns = [col['name'] for col in inspector.get_columns('usage_counters')]
        
        if 'video_render_count' in columns:
            op.drop_column('usage_counters', 'video_render_count')
        
        if 'voiceover_count' in columns:
            op.drop_column('usage_counters', 'voiceover_count')

