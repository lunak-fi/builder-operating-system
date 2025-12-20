"""add_operator_needs_review_to_deals

Revision ID: 2fe6130ef042
Revises: 372bb9d35aa5
Create Date: 2025-12-19 21:40:32.335533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fe6130ef042'
down_revision: Union[str, None] = '372bb9d35aa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('deals',
        sa.Column('operator_needs_review', sa.Boolean(),
                  nullable=False,
                  server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('deals', 'operator_needs_review')
