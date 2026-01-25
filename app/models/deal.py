from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, Integer, Numeric, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


# Deal status constants
class DealStatus:
    INBOX = "inbox"
    PENDING = "pending"
    SCREENING = "screening"
    UNDER_REVIEW = "under_review"
    DUE_DILIGENCE = "due_diligence"
    TERM_SHEET = "term_sheet"
    COMMITTED = "committed"
    PASSED = "passed"


# Forward progression chain (next stage mapping)
DEAL_STATUS_PROGRESSION = {
    "received": DealStatus.UNDER_REVIEW,  # New deals created by auto-populate
    DealStatus.INBOX: DealStatus.UNDER_REVIEW,
    DealStatus.PENDING: DealStatus.UNDER_REVIEW,
    DealStatus.SCREENING: DealStatus.UNDER_REVIEW,
    DealStatus.UNDER_REVIEW: DealStatus.DUE_DILIGENCE,
    DealStatus.DUE_DILIGENCE: DealStatus.TERM_SHEET,
    DealStatus.TERM_SHEET: DealStatus.COMMITTED,
    DealStatus.COMMITTED: None,  # Terminal state
    DealStatus.PASSED: None,  # Terminal state (but can be reversed)
}


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    internal_code: Mapped[str] = mapped_column(Text, nullable=False)
    deal_name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False, default="USA")
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    msa: Mapped[str | None] = mapped_column(Text, nullable=True)
    submarket: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    msa_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    building_sf: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hold_period_years: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="inbox")
    operator_needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    operator: Mapped["Operator"] = relationship("Operator", back_populates="deals")
    deal_operators: Mapped[list["DealOperator"]] = relationship(
        "DealOperator", back_populates="deal", cascade="all, delete-orphan"
    )
    documents: Mapped[list["DealDocument"]] = relationship(
        "DealDocument", back_populates="deal", cascade="all, delete-orphan"
    )
    underwriting: Mapped["DealUnderwriting"] = relationship(
        "DealUnderwriting", back_populates="deal", uselist=False, cascade="all, delete-orphan"
    )
    memos: Mapped[list["Memo"]] = relationship(
        "Memo", back_populates="deal", cascade="all, delete-orphan"
    )
    stage_transitions: Mapped[list["DealStageTransition"]] = relationship(
        "DealStageTransition", back_populates="deal", cascade="all, delete-orphan"
    )

    # Helper properties for multiple operators
    @property
    def operators(self) -> list["Operator"]:
        """Get all operators, primary first"""
        return [do.operator for do in sorted(
            self.deal_operators, key=lambda x: not x.is_primary
        )]

    @property
    def primary_operator(self) -> "Operator | None":
        """Get primary operator (for legacy code)"""
        primary = next((do for do in self.deal_operators if do.is_primary), None)
        return primary.operator if primary else None
