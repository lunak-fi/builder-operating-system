"""remove_funds_functionality

Revision ID: 5d5ddcd818ee
Revises: 2fe6130ef042
Create Date: 2026-01-15 22:04:39.405464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5d5ddcd818ee'
down_revision: Union[str, None] = '2fe6130ef042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraints first
    op.drop_constraint('deal_documents_fund_id_fkey', 'deal_documents', type_='foreignkey')
    op.drop_constraint('deals_fund_id_fkey', 'deals', type_='foreignkey')

    # Drop columns from dependent tables
    op.drop_column('deals', 'fund_id')
    op.drop_column('deal_documents', 'fund_id')
    op.drop_column('deal_documents', 'document_classification')

    # Drop funds table
    op.drop_table('funds')


def downgrade() -> None:
    # Recreate funds table (mirror of original migration 372bb9d35aa5)
    op.create_table('funds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operator_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('strategy', sa.Text(), nullable=True),
        sa.Column('target_irr', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('target_equity_multiple', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('target_geography', sa.Text(), nullable=True),
        sa.Column('target_asset_types', sa.Text(), nullable=True),
        sa.Column('fund_size', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('gp_commitment', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('management_fee', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('carried_interest', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('preferred_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['operator_id'], ['operators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add columns back to dependent tables
    op.add_column('deals', sa.Column('fund_id', sa.UUID(), nullable=True))
    op.create_foreign_key('deals_fund_id_fkey', 'deals', 'funds', ['fund_id'], ['id'], ondelete='SET NULL')

    op.add_column('deal_documents', sa.Column('fund_id', sa.UUID(), nullable=True))
    op.add_column('deal_documents', sa.Column('document_classification', sa.Text(), nullable=True))
    op.create_foreign_key('deal_documents_fund_id_fkey', 'deal_documents', 'funds', ['fund_id'], ['id'], ondelete='CASCADE')
