"""add user model preferences

Revision ID: 0607bc5b8547
Revises: 0607bc5b8546
Create Date: 2026-01-26 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0607bc5b8547'
down_revision = '0607bc5b8546'
branch_labels = None
depends_on = None


def upgrade():
    """Create user_model_preferences table"""
    op.create_table(
        'user_model_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_admin_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'content_type', name='uq_user_content_type')
    )
    op.create_index(op.f('ix_user_model_preferences_user_id'), 'user_model_preferences', ['user_id'], unique=False)


def downgrade():
    """Drop user_model_preferences table"""
    op.drop_index(op.f('ix_user_model_preferences_user_id'), table_name='user_model_preferences')
    op.drop_table('user_model_preferences')
