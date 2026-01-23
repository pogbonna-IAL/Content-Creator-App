"""add invoices and billing addresses

Revision ID: 0607bc5b8542
Revises: 0607bc5b8541
Create Date: 2026-01-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '0607bc5b8542'
down_revision = '0607bc5b8541'
branch_labels = None
depends_on = None


def upgrade():
    # Get list of existing tables
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Ensure organizations table exists (required for foreign keys)
    if 'organizations' not in tables:
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
        tables.append('organizations')
    
    # Ensure subscriptions table exists (required for invoices foreign key)
    if 'subscriptions' not in tables:
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('org_id', sa.Integer(), nullable=False),
            sa.Column('plan', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('provider', sa.String(), nullable=True),
            sa.Column('provider_customer_id', sa.String(), nullable=True),
            sa.Column('provider_subscription_id', sa.String(), nullable=True),
            sa.Column('current_period_end', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
        op.create_index(op.f('ix_subscriptions_org_id'), 'subscriptions', ['org_id'], unique=False)
        op.create_index(op.f('ix_subscriptions_plan'), 'subscriptions', ['plan'], unique=False)
        op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
        op.create_index(op.f('ix_subscriptions_provider_customer_id'), 'subscriptions', ['provider_customer_id'], unique=False)
        op.create_index(op.f('ix_subscriptions_provider_subscription_id'), 'subscriptions', ['provider_subscription_id'], unique=True)
        tables.append('subscriptions')
    
    # Create billing_addresses table
    op.create_table(
        'billing_addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('contact_name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address_line1', sa.String(length=200), nullable=False),
        sa.Column('address_line2', sa.String(length=200), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state_province', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('tax_id_type', sa.String(length=20), nullable=True),
        sa.Column('tax_id_verified', sa.Boolean(), default=False),
        sa.Column('customer_type', sa.String(length=20), default='individual'),
        sa.Column('tax_exempt', sa.Boolean(), default=False),
        sa.Column('tax_exempt_reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.UniqueConstraint('organization_id')
    )
    op.create_index(op.f('ix_billing_addresses_id'), 'billing_addresses', ['id'], unique=False)
    op.create_index(op.f('ix_billing_addresses_organization_id'), 'billing_addresses', ['organization_id'], unique=True)
    op.create_index(op.f('ix_billing_addresses_country_code'), 'billing_addresses', ['country_code'], unique=False)
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), default=0.00, nullable=False),
        sa.Column('total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), default=0.00),
        sa.Column('amount_due', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), default='USD', nullable=False),
        sa.Column('status', sa.String(length=20), default='draft', nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('void_at', sa.DateTime(), nullable=True),
        sa.Column('tax_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('line_items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('customer_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('pdf_generated_at', sa.DateTime(), nullable=True),
        sa.Column('provider', sa.String(length=20), nullable=True),
        sa.Column('provider_invoice_id', sa.String(length=100), nullable=True),
        sa.Column('provider_payment_intent_id', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('memo', sa.String(length=500), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # Renamed from 'metadata' - reserved in SQLAlchemy
        sa.Column('emailed_to', sa.String(length=255), nullable=True),
        sa.Column('emailed_at', sa.DateTime(), nullable=True),
        sa.Column('email_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.UniqueConstraint('invoice_number')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)
    op.create_index(op.f('ix_invoices_organization_id'), 'invoices', ['organization_id'], unique=False)
    op.create_index(op.f('ix_invoices_subscription_id'), 'invoices', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_invoices_status'), 'invoices', ['status'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_date'), 'invoices', ['invoice_date'], unique=False)
    op.create_index(op.f('ix_invoices_due_date'), 'invoices', ['due_date'], unique=False)
    op.create_index(op.f('ix_invoices_provider_invoice_id'), 'invoices', ['provider_invoice_id'], unique=False)
    
    # Composite indexes
    op.create_index('idx_invoices_org_date', 'invoices', ['organization_id', 'invoice_date'], unique=False)
    op.create_index('idx_invoices_status_date', 'invoices', ['status', 'invoice_date'], unique=False)
    op.create_index('idx_invoices_due_date', 'invoices', ['due_date', 'status'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('idx_invoices_due_date', table_name='invoices')
    op.drop_index('idx_invoices_status_date', table_name='invoices')
    op.drop_index('idx_invoices_org_date', table_name='invoices')
    op.drop_index(op.f('ix_invoices_provider_invoice_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_due_date'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_date'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_status'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_subscription_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_organization_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    
    # Drop tables
    op.drop_table('invoices')
    
    op.drop_index(op.f('ix_billing_addresses_country_code'), table_name='billing_addresses')
    op.drop_index(op.f('ix_billing_addresses_organization_id'), table_name='billing_addresses')
    op.drop_index(op.f('ix_billing_addresses_id'), table_name='billing_addresses')
    op.drop_table('billing_addresses')

