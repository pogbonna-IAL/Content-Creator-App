"""add user deleted_at for GDPR

Revision ID: 0607bc5b8538
Revises: 0607bc5b8537
Create Date: 2026-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0607bc5b8538'
down_revision = '0607bc5b8537'
branch_labels = None
depends_on = None


def upgrade():
    """Add deleted_at column to users table for GDPR soft delete"""
    # Add deleted_at column to users table
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    # Add index on deleted_at for efficient queries
    op.create_index(
        'idx_users_deleted_at',
        'users',
        ['deleted_at'],
        unique=False
    )


def downgrade():
    """Remove deleted_at column from users table"""
    # Drop index
    op.drop_index('idx_users_deleted_at', table_name='users')
    
    # Drop column
    op.drop_column('users', 'deleted_at')

