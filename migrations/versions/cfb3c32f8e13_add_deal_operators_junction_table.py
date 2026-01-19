"""add_deal_operators_junction_table

Revision ID: cfb3c32f8e13
Revises: 4a989339ab59
Create Date: 2026-01-18 21:58:31.271727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfb3c32f8e13'
down_revision: Union[str, None] = '4a989339ab59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create deal_operators junction table
    op.create_table(
        'deal_operators',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=False),
        sa.Column('operator_id', sa.UUID(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['operator_id'], ['operators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deal_id', 'operator_id', name='uq_deal_operator')
    )

    # Migrate existing data from deals.operator_id to deal_operators
    # This ensures all existing deals have their primary operator in the junction table
    op.execute("""
        INSERT INTO deal_operators (id, deal_id, operator_id, is_primary, created_at)
        SELECT gen_random_uuid(), id, operator_id, true, now()
        FROM deals
        WHERE operator_id IS NOT NULL
    """)


def downgrade() -> None:
    # Drop the junction table
    op.drop_table('deal_operators')
