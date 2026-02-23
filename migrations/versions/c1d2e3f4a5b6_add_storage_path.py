"""add_storage_path

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-02-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('deal_documents', sa.Column('storage_path', sa.Text(), nullable=True))
    op.add_column('pending_email_attachments', sa.Column('storage_path', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('pending_email_attachments', 'storage_path')
    op.drop_column('deal_documents', 'storage_path')
