"""add media generation counters

Revision ID: 0607bc5b8536
Revises: 0607bc5b8535
Create Date: 2026-01-12 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0607bc5b8536'
down_revision = '0607bc5b8535'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add voiceover_count and video_render_count columns to usage_counters table
    op.add_column('usage_counters', sa.Column('voiceover_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('usage_counters', sa.Column('video_render_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove columns
    op.drop_column('usage_counters', 'video_render_count')
    op.drop_column('usage_counters', 'voiceover_count')

