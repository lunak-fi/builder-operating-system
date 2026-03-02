from datetime import datetime
from typing import Optional
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import Base


class SponsorNote(Base):
    __tablename__ = "sponsor_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    note_type: Mapped[str] = mapped_column(Text, nullable=False)  # 'quick_note', 'meeting_log', 'call_log', 'email_summary'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    interaction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    operator: Mapped["Operator"] = relationship("Operator", back_populates="sponsor_notes")
