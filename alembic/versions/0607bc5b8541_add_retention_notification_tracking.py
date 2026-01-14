"""add_retention_notification_tracking

Revision ID: 0607bc5b8541
Revises: 0607bc5b8540
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0607bc5b8541'
down_revision = '0607bc5b8540'
branch_labels = None
depends_on = None


def upgrade():
    """Add retention notification tracking table"""
    
    # Create retention_notifications table
    op.create_table(
        'retention_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('artifact_id', sa.Integer(), nullable=False),
        sa.Column('notification_date', sa.Date(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        sa.Column('artifact_type', sa.String(length=50), nullable=False),
        sa.Column('artifact_topic', sa.String(length=500), nullable=True),
        sa.Column('email_sent', sa.Boolean(), default=False, nullable=False),
        sa.Column('email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('email_failed', sa.Boolean(), default=False, nullable=False),
        sa.Column('failure_reason', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient queries
    op.create_index(
        'idx_retention_notifications_user_artifact',
        'retention_notifications',
        ['user_id', 'artifact_id', 'notification_date'],
        unique=True  # Prevent duplicate notifications for same artifact on same date
    )
    
    op.create_index(
        'idx_retention_notifications_artifact',
        'retention_notifications',
        ['artifact_id']
    )
    
    op.create_index(
        'idx_retention_notifications_notification_date',
        'retention_notifications',
        ['notification_date']
    )
    
    op.create_index(
        'idx_retention_notifications_email_status',
        'retention_notifications',
        ['email_sent', 'notification_date']
    )
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_retention_notifications_user',
        'retention_notifications',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_retention_notifications_organization',
        'retention_notifications',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_retention_notifications_artifact',
        'retention_notifications',
        'content_artifacts',
        ['artifact_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    """Remove retention notification tracking table"""
    
    # Drop foreign keys
    op.drop_constraint(
        'fk_retention_notifications_artifact',
        'retention_notifications',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_retention_notifications_organization',
        'retention_notifications',
        type_='foreignkey'
    )
    op.drop_constraint(
        'fk_retention_notifications_user',
        'retention_notifications',
        type_='foreignkey'
    )
    
    # Drop indexes
    op.drop_index('idx_retention_notifications_email_status', table_name='retention_notifications')
    op.drop_index('idx_retention_notifications_notification_date', table_name='retention_notifications')
    op.drop_index('idx_retention_notifications_artifact', table_name='retention_notifications')
    op.drop_index('idx_retention_notifications_user_artifact', table_name='retention_notifications')
    
    # Drop table
    op.drop_table('retention_notifications')

