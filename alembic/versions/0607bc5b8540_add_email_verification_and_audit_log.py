"""add email verification and audit log

Revision ID: 0607bc5b8540
Revises: 0607bc5b8539
Create Date: 2026-01-13 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0607bc5b8540'
down_revision: Union[str, Sequence[str], None] = '0607bc5b8539'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email verification and audit logging support."""
    
    # 1. Add email_verified column to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verification_sent_at', sa.DateTime(), nullable=True))
    
    # Add index for verification token lookups
    op.create_index('idx_users_verification_token', 'users', ['email_verification_token'], unique=False)
    
    # 2. Create audit_log table (append-only for compliance)
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),  # LOGIN_SUCCESS, LOGIN_FAIL, etc.
        sa.Column('actor_user_id', sa.Integer(), nullable=True),  # NULL for anonymous actions
        sa.Column('target_user_id', sa.Integer(), nullable=True),  # User affected by action (if different from actor)
        sa.Column('ip_hash', sa.String(), nullable=True),  # SHA256 hash of IP (PII protection)
        sa.Column('user_agent_hash', sa.String(), nullable=True),  # SHA256 hash of user agent
        sa.Column('details', sa.JSON(), nullable=True),  # Additional context (no PII)
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Indexes for audit_log queries
    op.create_index('idx_audit_log_action_type', 'audit_log', ['action_type'], unique=False)
    op.create_index('idx_audit_log_actor_user_id', 'audit_log', ['actor_user_id'], unique=False)
    op.create_index('idx_audit_log_created_at_desc', 'audit_log', [sa.text('created_at DESC')], unique=False)
    op.create_index('idx_audit_log_actor_created', 'audit_log', ['actor_user_id', sa.text('created_at DESC')], unique=False)


def downgrade() -> None:
    """Remove email verification and audit logging."""
    
    # Drop audit_log indexes and table
    op.drop_index('idx_audit_log_actor_created', table_name='audit_log')
    op.drop_index('idx_audit_log_created_at_desc', table_name='audit_log')
    op.drop_index('idx_audit_log_actor_user_id', table_name='audit_log')
    op.drop_index('idx_audit_log_action_type', table_name='audit_log')
    op.drop_table('audit_log')
    
    # Drop email verification columns
    op.drop_index('idx_users_verification_token', table_name='users')
    op.drop_column('users', 'email_verification_sent_at')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')

