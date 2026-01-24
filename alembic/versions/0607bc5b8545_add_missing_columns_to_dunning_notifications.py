"""add missing columns to dunning_notifications

Revision ID: 0607bc5b8545
Revises: 0607bc5b8544
Create Date: 2026-01-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0607bc5b8545'
down_revision = '0607bc5b8544'
branch_labels = None
depends_on = None


def upgrade():
    # Check if dunning_notifications table exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    if 'dunning_notifications' in tables:
        # Check if created_at column already exists
        columns = [col['name'] for col in inspector.get_columns('dunning_notifications')]
        
        # Add created_at column if it doesn't exist
        if 'created_at' not in columns:
            op.add_column('dunning_notifications',
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
            )
        
        # Add updated_at column if it doesn't exist
        if 'updated_at' not in columns:
            op.add_column('dunning_notifications',
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
            )
    # If table doesn't exist, the original migration will create it with the columns


def downgrade():
    # Check if dunning_notifications table exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    if 'dunning_notifications' in tables:
        # Check if columns exist before dropping
        columns = [col['name'] for col in inspector.get_columns('dunning_notifications')]
        
        if 'updated_at' in columns:
            op.drop_column('dunning_notifications', 'updated_at')
        
        if 'created_at' in columns:
            op.drop_column('dunning_notifications', 'created_at')
