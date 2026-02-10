"""
PendingEmail model for storing inbound emails pending user review.

When users forward deal emails to deals+{org_id}@buildingpartnership.co,
emails are stored here until the user reviews and confirms them to create deals.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Text, DateTime, ForeignKey, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import Base

if TYPE_CHECKING:
    from .pending_email_attachment import PendingEmailAttachment


class PendingEmail(Base):
    """
    Stores inbound emails pending user review before deal creation.

    Status flow: received -> processing -> ready_for_review -> confirmed/failed
    """
    __tablename__ = "pending_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Organization association (extracted from deals+{org_id}@domain.com)
    organization_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # Processing status
    # received: email received, not yet processed
    # processing: AI extraction in progress
    # ready_for_review: extraction complete, awaiting user confirmation
    # confirmed: user confirmed and deal created
    # failed: processing failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="received")

    # Email metadata
    from_address: Mapped[str] = mapped_column(Text, nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Original email data
    to_addresses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    cc_addresses: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    email_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    in_reply_to: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Storage for raw .eml file (optional)
    raw_email_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI extraction results (same structure as ExtractionPreviewResponse)
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    operator_matches: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Resulting deal (set after confirmation)
    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    attachments: Mapped[List["PendingEmailAttachment"]] = relationship(
        "PendingEmailAttachment",
        back_populates="pending_email",
        cascade="all, delete-orphan"
    )
