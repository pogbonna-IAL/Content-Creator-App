"""add user is_admin flag

Revision ID: 0607bc5b8544
Revises: 0607bc5b8543
Create Date: 2026-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0607bc5b8544'
down_revision = '0607bc5b8543'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_admin column to users table
    # Default to False for backward compatibility (existing users are not admins)
    op.add_column('users', 
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Create index for faster admin queries
    op.create_index('ix_users_is_admin', 'users', ['is_admin'], unique=False)
    
    # Note: To make a user an admin, run:
    # UPDATE users SET is_admin = true WHERE id = <user_id>;
    # Or use the admin management script/endpoint


def downgrade():
    # Remove index
    op.drop_index('ix_users_is_admin', table_name='users')
    
    # Remove column
    op.drop_column('users', 'is_admin')
