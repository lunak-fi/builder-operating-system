"""add_asset_type_details_to_deals

Revision ID: f3a8b2c1d4e5
Revises: cadca2cd339b
Create Date: 2026-02-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f3a8b2c1d4e5'
down_revision: Union[str, None] = 'cadca2cd339b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add asset_type_details JSONB column to deals table
    # This stores asset-type-specific fields (retail, industrial, office, mixed-use)
    op.add_column('deals', sa.Column('asset_type_details', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('deals', 'asset_type_details')
