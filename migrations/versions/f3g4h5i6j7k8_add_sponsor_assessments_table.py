"""add sponsor_assessments table

Revision ID: f3g4h5i6j7k8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3g4h5i6j7k8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sponsor_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('operators.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('dimensions', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_sponsor_assessments_operator_id', 'sponsor_assessments', ['operator_id'])


def downgrade() -> None:
    op.drop_index('ix_sponsor_assessments_operator_id', table_name='sponsor_assessments')
    op.drop_table('sponsor_assessments')
