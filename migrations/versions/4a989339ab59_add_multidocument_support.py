"""add_multidocument_support

Revision ID: 4a989339ab59
Revises: 5d5ddcd818ee
Create Date: 2026-01-16 14:27:53.755288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4a989339ab59'
down_revision: Union[str, None] = '5d5ddcd818ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for multi-document support
    op.add_column('deal_documents', sa.Column('file_size', sa.BigInteger(), nullable=True))
    op.add_column('deal_documents', sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('deal_documents', sa.Column('parent_document_id', sa.UUID(), nullable=True))
    op.add_column('deal_documents', sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'))

    # Add foreign key for parent_document_id (self-referential)
    op.create_foreign_key(
        'deal_documents_parent_document_id_fkey',
        'deal_documents',
        'deal_documents',
        ['parent_document_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add indexes for timeline queries and version tracking
    op.create_index('idx_deal_documents_timeline', 'deal_documents', ['deal_id', sa.text('created_at DESC')])
    op.create_index('idx_deal_documents_versions', 'deal_documents', ['parent_document_id', 'version_number'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_deal_documents_versions', table_name='deal_documents')
    op.drop_index('idx_deal_documents_timeline', table_name='deal_documents')

    # Drop foreign key
    op.drop_constraint('deal_documents_parent_document_id_fkey', 'deal_documents', type_='foreignkey')

    # Drop columns
    op.drop_column('deal_documents', 'version_number')
    op.drop_column('deal_documents', 'parent_document_id')
    op.drop_column('deal_documents', 'metadata_json')
    op.drop_column('deal_documents', 'file_size')
