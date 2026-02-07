"""add_deal_notes_table

Revision ID: a1b2c3d4e5f6
Revises: f3a8b2c1d4e5
Create Date: 2026-02-06 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f3a8b2c1d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create deal_notes table
    op.create_table(
        'deal_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('deal_id', UUID(as_uuid=True), sa.ForeignKey('deals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_name', sa.Text, nullable=True),
        sa.Column('note_type', sa.Text, nullable=False),  # 'quick_note', 'thread_summary'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata_json', JSONB, nullable=True),  # AI insights for thread_summary
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create index on deal_id for fast lookups
    op.create_index('idx_deal_notes_deal_id', 'deal_notes', ['deal_id'])


def downgrade() -> None:
    op.drop_index('idx_deal_notes_deal_id', 'deal_notes')
    op.drop_table('deal_notes')
