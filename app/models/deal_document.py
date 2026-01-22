from datetime import datetime
from typing import Optional, List
from sqlalchemy import Text, DateTime, ForeignKey, func, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import Base


class DealDocument(Base):
    __tablename__ = "deal_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsing_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    parsing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # New fields for multi-document support
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal_documents.id", ondelete="SET NULL"), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Document event date (report date, email date, conversation date, etc.)
    # Falls back to created_at if not specified
    document_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    deal: Mapped["Deal"] = relationship("Deal", back_populates="documents")

    # Self-referential relationship for document versions
    versions: Mapped[List["DealDocument"]] = relationship(
        "DealDocument",
        back_populates="parent",
        foreign_keys=[parent_document_id],
        cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["DealDocument"]] = relationship(
        "DealDocument",
        back_populates="versions",
        remote_side=[id],
        foreign_keys=[parent_document_id]
    )
