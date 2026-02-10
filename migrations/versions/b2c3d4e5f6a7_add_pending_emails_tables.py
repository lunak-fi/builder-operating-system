"""add_pending_emails_tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-09 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pending_emails table
    op.create_table(
        'pending_emails',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.Text, nullable=False),
        sa.Column('status', sa.Text, nullable=False, server_default='received'),
        # Email metadata
        sa.Column('from_address', sa.Text, nullable=False),
        sa.Column('from_name', sa.Text, nullable=True),
        sa.Column('subject', sa.Text, nullable=False),
        sa.Column('body_text', sa.Text, nullable=True),
        sa.Column('body_html', sa.Text, nullable=True),
        sa.Column('to_addresses', JSONB, nullable=True),
        sa.Column('cc_addresses', JSONB, nullable=True),
        sa.Column('email_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_id', sa.Text, nullable=True),
        sa.Column('in_reply_to', sa.Text, nullable=True),
        sa.Column('raw_headers', JSONB, nullable=True),
        sa.Column('raw_email_url', sa.Text, nullable=True),
        # Extraction results
        sa.Column('extracted_data', JSONB, nullable=True),
        sa.Column('operator_matches', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        # Resulting deal
        sa.Column('deal_id', UUID(as_uuid=True), sa.ForeignKey('deals.id', ondelete='SET NULL'), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('idx_pending_emails_org_id', 'pending_emails', ['organization_id'])
    op.create_index('idx_pending_emails_status', 'pending_emails', ['status'])
    op.create_index('idx_pending_emails_created_at', 'pending_emails', ['created_at'])

    # Create pending_email_attachments table
    op.create_table(
        'pending_email_attachments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('pending_email_id', UUID(as_uuid=True), sa.ForeignKey('pending_emails.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.Text, nullable=False),
        sa.Column('content_type', sa.Text, nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('storage_url', sa.Text, nullable=False),
        sa.Column('parsing_status', sa.Text, nullable=False, server_default='pending'),
        sa.Column('parsed_text', sa.Text, nullable=True),
        sa.Column('parsing_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create index on pending_email_id
    op.create_index('idx_pending_email_attachments_email_id', 'pending_email_attachments', ['pending_email_id'])


def downgrade() -> None:
    op.drop_index('idx_pending_email_attachments_email_id', 'pending_email_attachments')
    op.drop_table('pending_email_attachments')
    op.drop_index('idx_pending_emails_created_at', 'pending_emails')
    op.drop_index('idx_pending_emails_status', 'pending_emails')
    op.drop_index('idx_pending_emails_org_id', 'pending_emails')
    op.drop_table('pending_emails')
