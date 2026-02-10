"""
PendingEmailAttachment model for storing attachments from pending emails.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Text, DateTime, ForeignKey, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

if TYPE_CHECKING:
    from .pending_email import PendingEmail


class PendingEmailAttachment(Base):
    """
    Stores attachments from pending emails.
    """
    __tablename__ = "pending_email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Parent email reference
    pending_email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pending_emails.id", ondelete="CASCADE"), nullable=False
    )

    # File info
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)

    # Parsing status for PDFs/Excel files
    parsing_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pending_email: Mapped["PendingEmail"] = relationship(
        "PendingEmail",
        back_populates="attachments"
    )
