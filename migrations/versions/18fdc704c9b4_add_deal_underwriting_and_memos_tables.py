"""Add deal_underwriting and memos tables

Revision ID: 18fdc704c9b4
Revises: 1bd3146a267e
Create Date: 2025-11-28 18:06:43.812952

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '18fdc704c9b4'
down_revision: Union[str, None] = '1bd3146a267e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create deal_underwriting table
    op.create_table(
        'deal_underwriting',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version_label', sa.Text(), nullable=True),
        sa.Column('total_project_cost', sa.Numeric(), nullable=True),
        sa.Column('land_cost', sa.Numeric(), nullable=True),
        sa.Column('hard_cost', sa.Numeric(), nullable=True),
        sa.Column('soft_cost', sa.Numeric(), nullable=True),
        sa.Column('loan_amount', sa.Numeric(), nullable=True),
        sa.Column('equity_required', sa.Numeric(), nullable=True),
        sa.Column('interest_rate', sa.Numeric(), nullable=True),
        sa.Column('ltv', sa.Numeric(), nullable=True),
        sa.Column('ltc', sa.Numeric(), nullable=True),
        sa.Column('dscr_at_stabilization', sa.Numeric(), nullable=True),
        sa.Column('levered_irr', sa.Numeric(), nullable=True),
        sa.Column('unlevered_irr', sa.Numeric(), nullable=True),
        sa.Column('equity_multiple', sa.Numeric(), nullable=True),
        sa.Column('avg_cash_on_cash', sa.Numeric(), nullable=True),
        sa.Column('project_duration_years', sa.Numeric(), nullable=True),
        sa.Column('exit_cap_rate', sa.Numeric(), nullable=True),
        sa.Column('yield_on_cost', sa.Numeric(), nullable=True),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_document_id'], ['deal_documents.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deal_id')
    )

    # Create memos table
    op.create_table(
        'memos',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('memo_type', sa.Text(), server_default='investment_memo', nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('generated_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('memos')
    op.drop_table('deal_underwriting')
