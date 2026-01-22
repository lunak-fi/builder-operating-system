"""add_document_date_to_deal_documents

Revision ID: a6ff26c3b4fe
Revises: cfb3c32f8e13
Create Date: 2026-01-22 11:09:40.958552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6ff26c3b4fe'
down_revision: Union[str, None] = 'cfb3c32f8e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add document_date column to deal_documents table
    op.add_column('deal_documents',
        sa.Column('document_date', sa.DateTime(timezone=True), nullable=True))

    # Backfill existing records: set document_date = created_at as default
    op.execute("""
        UPDATE deal_documents
        SET document_date = created_at
        WHERE document_date IS NULL
    """)

    # For transcripts with conversation_date in metadata, use that instead
    # metadata_json structure: {"transcript": {"conversation_date": "2026-01-15T14:30:00Z"}, ...}
    op.execute("""
        UPDATE deal_documents
        SET document_date = (metadata_json->'transcript'->>'conversation_date')::TIMESTAMP WITH TIME ZONE
        WHERE document_type = 'transcript'
          AND metadata_json IS NOT NULL
          AND metadata_json->'transcript' IS NOT NULL
          AND metadata_json->'transcript'->>'conversation_date' IS NOT NULL
          AND metadata_json->'transcript'->>'conversation_date' != ''
    """)


def downgrade() -> None:
    # Drop the document_date column
    op.drop_column('deal_documents', 'document_date')
