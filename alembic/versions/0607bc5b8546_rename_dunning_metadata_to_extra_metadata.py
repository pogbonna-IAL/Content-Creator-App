"""rename dunning metadata to extra_metadata

Revision ID: 0607bc5b8546
Revises: 0607bc5b8545
Create Date: 2026-01-24 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0607bc5b8546'
down_revision = '0607bc5b8545'
branch_labels = None
depends_on = None


def upgrade():
    """
    Rename 'metadata' column to 'extra_metadata' in dunning-related tables
    This avoids SQLAlchemy reserved keyword conflicts
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Rename metadata to extra_metadata in dunning_processes
    if 'dunning_processes' in tables:
        columns = [col['name'] for col in inspector.get_columns('dunning_processes')]
        if 'metadata' in columns and 'extra_metadata' not in columns:
            op.alter_column('dunning_processes', 'metadata',
                          new_column_name='extra_metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'metadata' to 'extra_metadata' in dunning_processes")
        elif 'extra_metadata' in columns:
            print("'extra_metadata' already exists in dunning_processes, skipping")
        else:
            # Column doesn't exist, add it
            op.add_column('dunning_processes',
                sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            print("Added 'extra_metadata' column to dunning_processes")
    
    # Rename metadata to extra_metadata in payment_attempts
    if 'payment_attempts' in tables:
        columns = [col['name'] for col in inspector.get_columns('payment_attempts')]
        if 'metadata' in columns and 'extra_metadata' not in columns:
            op.alter_column('payment_attempts', 'metadata',
                          new_column_name='extra_metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'metadata' to 'extra_metadata' in payment_attempts")
        elif 'extra_metadata' in columns:
            print("'extra_metadata' already exists in payment_attempts, skipping")
        else:
            # Column doesn't exist, add it
            op.add_column('payment_attempts',
                sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            print("Added 'extra_metadata' column to payment_attempts")
    
    # Rename metadata to extra_metadata in dunning_notifications
    if 'dunning_notifications' in tables:
        columns = [col['name'] for col in inspector.get_columns('dunning_notifications')]
        if 'metadata' in columns and 'extra_metadata' not in columns:
            op.alter_column('dunning_notifications', 'metadata',
                          new_column_name='extra_metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'metadata' to 'extra_metadata' in dunning_notifications")
        elif 'extra_metadata' in columns:
            print("'extra_metadata' already exists in dunning_notifications, skipping")
        else:
            # Column doesn't exist, add it
            op.add_column('dunning_notifications',
                sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            print("Added 'extra_metadata' column to dunning_notifications")


def downgrade():
    """
    Rename 'extra_metadata' back to 'metadata' in dunning-related tables
    """
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Rename extra_metadata back to metadata in dunning_processes
    if 'dunning_processes' in tables:
        columns = [col['name'] for col in inspector.get_columns('dunning_processes')]
        if 'extra_metadata' in columns and 'metadata' not in columns:
            op.alter_column('dunning_processes', 'extra_metadata',
                          new_column_name='metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'extra_metadata' back to 'metadata' in dunning_processes")
    
    # Rename extra_metadata back to metadata in payment_attempts
    if 'payment_attempts' in tables:
        columns = [col['name'] for col in inspector.get_columns('payment_attempts')]
        if 'extra_metadata' in columns and 'metadata' not in columns:
            op.alter_column('payment_attempts', 'extra_metadata',
                          new_column_name='metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'extra_metadata' back to 'metadata' in payment_attempts")
    
    # Rename extra_metadata back to metadata in dunning_notifications
    if 'dunning_notifications' in tables:
        columns = [col['name'] for col in inspector.get_columns('dunning_notifications')]
        if 'extra_metadata' in columns and 'metadata' not in columns:
            op.alter_column('dunning_notifications', 'extra_metadata',
                          new_column_name='metadata',
                          existing_type=postgresql.JSONB(astext_type=sa.Text()),
                          existing_nullable=True)
            print("Renamed 'extra_metadata' back to 'metadata' in dunning_notifications")
