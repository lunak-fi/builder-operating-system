"""Add deals and deal_documents tables

Revision ID: 1bd3146a267e
Revises: 79df4a9ae6de
Create Date: 2025-11-28 18:03:23.841809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1bd3146a267e'
down_revision: Union[str, None] = '79df4a9ae6de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create deals table
    op.create_table(
        'deals',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('internal_code', sa.Text(), nullable=False),
        sa.Column('deal_name', sa.Text(), nullable=False),
        sa.Column('country', sa.Text(), server_default='USA', nullable=False),
        sa.Column('state', sa.Text(), nullable=True),
        sa.Column('msa', sa.Text(), nullable=True),
        sa.Column('submarket', sa.Text(), nullable=True),
        sa.Column('address_line1', sa.Text(), nullable=True),
        sa.Column('postal_code', sa.Text(), nullable=True),
        sa.Column('asset_type', sa.Text(), nullable=True),
        sa.Column('strategy_type', sa.Text(), nullable=True),
        sa.Column('num_units', sa.Integer(), nullable=True),
        sa.Column('building_sf', sa.Numeric(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('business_plan_summary', sa.Text(), nullable=True),
        sa.Column('hold_period_years', sa.Numeric(), nullable=True),
        sa.Column('status', sa.Text(), server_default='inbox', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['operator_id'], ['operators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create deal_documents table
    op.create_table(
        'deal_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.Text(), nullable=False),
        sa.Column('file_name', sa.Text(), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('source_description', sa.Text(), nullable=True),
        sa.Column('parsed_text', sa.Text(), nullable=True),
        sa.Column('parsing_status', sa.Text(), server_default='pending', nullable=False),
        sa.Column('parsing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop deal_documents table first (foreign key dependency)
    op.drop_table('deal_documents')
    # Drop deals table
    op.drop_table('deals')
