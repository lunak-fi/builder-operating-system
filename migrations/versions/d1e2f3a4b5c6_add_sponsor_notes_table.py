"""add_sponsor_notes_table

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sponsor_notes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('operator_id', UUID(as_uuid=True), sa.ForeignKey('operators.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_name', sa.Text, nullable=True),
        sa.Column('note_type', sa.Text, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('interaction_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('idx_sponsor_notes_operator_id', 'sponsor_notes', ['operator_id'])


def downgrade() -> None:
    op.drop_index('idx_sponsor_notes_operator_id', 'sponsor_notes')
    op.drop_table('sponsor_notes')
