"""add dunning and refunds

Revision ID: 0607bc5b8543
Revises: 0607bc5b8542
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0607bc5b8543'
down_revision = '0607bc5b8542'
branch_labels = None
depends_on = None


def upgrade():
    # Create dunning_processes table
    op.create_table(
        'dunning_processes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('amount_due', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('amount_recovered', sa.Numeric(precision=12, scale=2), default=0.00),
        sa.Column('currency', sa.String(length=3), default='USD', nullable=False),
        sa.Column('total_attempts', sa.Integer(), default=0),
        sa.Column('total_emails_sent', sa.Integer(), default=0),
        sa.Column('current_stage', sa.String(length=50), default='initial'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('next_action_at', sa.DateTime(), nullable=True),
        sa.Column('grace_period_ends_at', sa.DateTime(), nullable=True),
        sa.Column('will_cancel_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    )
    op.create_index(op.f('ix_dunning_processes_id'), 'dunning_processes', ['id'], unique=False)
    op.create_index(op.f('ix_dunning_processes_subscription_id'), 'dunning_processes', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_dunning_processes_organization_id'), 'dunning_processes', ['organization_id'], unique=False)
    op.create_index(op.f('ix_dunning_processes_status'), 'dunning_processes', ['status'], unique=False)
    op.create_index(op.f('ix_dunning_processes_next_action_at'), 'dunning_processes', ['next_action_at'], unique=False)
    op.create_index('idx_dunning_processes_subscription_status', 'dunning_processes', ['subscription_id', 'status'], unique=False)
    op.create_index('idx_dunning_processes_next_action', 'dunning_processes', ['next_action_at', 'status'], unique=False)
    
    # Create payment_attempts table
    op.create_table(
        'payment_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('dunning_process_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), default='USD', nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempt_number', sa.Integer(), default=1, nullable=False),
        sa.Column('is_automatic', sa.Boolean(), default=True),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('provider_payment_intent_id', sa.String(length=100), nullable=True),
        sa.Column('provider_charge_id', sa.String(length=100), nullable=True),
        sa.Column('failure_code', sa.String(length=50), nullable=True),
        sa.Column('failure_message', sa.String(length=500), nullable=True),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('max_retries', sa.Integer(), default=3),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.Column('succeeded_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['dunning_process_id'], ['dunning_processes.id'], ),
    )
    op.create_index(op.f('ix_payment_attempts_id'), 'payment_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_payment_attempts_subscription_id'), 'payment_attempts', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_payment_attempts_dunning_process_id'), 'payment_attempts', ['dunning_process_id'], unique=False)
    op.create_index(op.f('ix_payment_attempts_status'), 'payment_attempts', ['status'], unique=False)
    op.create_index(op.f('ix_payment_attempts_provider_payment_intent_id'), 'payment_attempts', ['provider_payment_intent_id'], unique=False)
    op.create_index(op.f('ix_payment_attempts_next_retry_at'), 'payment_attempts', ['next_retry_at'], unique=False)
    op.create_index('idx_payment_attempts_subscription_status', 'payment_attempts', ['subscription_id', 'status'], unique=False)
    op.create_index('idx_payment_attempts_next_retry', 'payment_attempts', ['next_retry_at', 'status'], unique=False)
    
    # Create dunning_notifications table
    op.create_table(
        'dunning_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dunning_process_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('sent_to', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=200), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('delivered', sa.Boolean(), nullable=True),
        sa.Column('opened', sa.Boolean(), nullable=True),
        sa.Column('clicked', sa.Boolean(), nullable=True),
        sa.Column('email_provider', sa.String(length=50), nullable=True),
        sa.Column('provider_message_id', sa.String(length=200), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dunning_process_id'], ['dunning_processes.id'], ),
    )
    op.create_index(op.f('ix_dunning_notifications_id'), 'dunning_notifications', ['id'], unique=False)
    op.create_index(op.f('ix_dunning_notifications_dunning_process_id'), 'dunning_notifications', ['dunning_process_id'], unique=False)
    
    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), default='USD', nullable=False),
        sa.Column('refund_type', sa.String(length=20), default='full'),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('reason_details', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('provider_refund_id', sa.String(length=100), nullable=True),
        sa.Column('provider_charge_id', sa.String(length=100), nullable=True),
        sa.Column('is_within_refund_window', sa.Boolean(), default=True),
        sa.Column('refund_window_days', sa.Integer(), nullable=True),
        sa.Column('days_since_payment', sa.Integer(), nullable=True),
        sa.Column('failure_reason', sa.String(length=200), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('requested_by', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
        sa.UniqueConstraint('provider_refund_id')
    )
    op.create_index(op.f('ix_refunds_id'), 'refunds', ['id'], unique=False)
    op.create_index(op.f('ix_refunds_subscription_id'), 'refunds', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_refunds_invoice_id'), 'refunds', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_refunds_organization_id'), 'refunds', ['organization_id'], unique=False)
    op.create_index(op.f('ix_refunds_status'), 'refunds', ['status'], unique=False)
    op.create_index(op.f('ix_refunds_provider_refund_id'), 'refunds', ['provider_refund_id'], unique=True)
    op.create_index('idx_refunds_org_status', 'refunds', ['organization_id', 'status'], unique=False)
    op.create_index('idx_refunds_subscription', 'refunds', ['subscription_id', 'created_at'], unique=False)


def downgrade():
    # Drop refunds table
    op.drop_index('idx_refunds_subscription', table_name='refunds')
    op.drop_index('idx_refunds_org_status', table_name='refunds')
    op.drop_index(op.f('ix_refunds_provider_refund_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_status'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_organization_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_invoice_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_subscription_id'), table_name='refunds')
    op.drop_index(op.f('ix_refunds_id'), table_name='refunds')
    op.drop_table('refunds')
    
    # Drop dunning_notifications table
    op.drop_index(op.f('ix_dunning_notifications_dunning_process_id'), table_name='dunning_notifications')
    op.drop_index(op.f('ix_dunning_notifications_id'), table_name='dunning_notifications')
    op.drop_table('dunning_notifications')
    
    # Drop payment_attempts table
    op.drop_index('idx_payment_attempts_next_retry', table_name='payment_attempts')
    op.drop_index('idx_payment_attempts_subscription_status', table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_next_retry_at'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_provider_payment_intent_id'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_status'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_dunning_process_id'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_subscription_id'), table_name='payment_attempts')
    op.drop_index(op.f('ix_payment_attempts_id'), table_name='payment_attempts')
    op.drop_table('payment_attempts')
    
    # Drop dunning_processes table
    op.drop_index('idx_dunning_processes_next_action', table_name='dunning_processes')
    op.drop_index('idx_dunning_processes_subscription_status', table_name='dunning_processes')
    op.drop_index(op.f('ix_dunning_processes_next_action_at'), table_name='dunning_processes')
    op.drop_index(op.f('ix_dunning_processes_status'), table_name='dunning_processes')
    op.drop_index(op.f('ix_dunning_processes_organization_id'), table_name='dunning_processes')
    op.drop_index(op.f('ix_dunning_processes_subscription_id'), table_name='dunning_processes')
    op.drop_index(op.f('ix_dunning_processes_id'), table_name='dunning_processes')
    op.drop_table('dunning_processes')

