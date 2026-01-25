from datetime import datetime
from decimal import Decimal
from sqlalchemy import Text, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import Base


class DealUnderwriting(Base):
    __tablename__ = "deal_underwriting"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deal_documents.id"), nullable=True
    )
    version_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_project_cost: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    land_cost: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    hard_cost: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    soft_cost: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    loan_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    equity_required: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    our_investment: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ltv: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ltc: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    dscr_at_stabilization: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    levered_irr: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    unlevered_irr: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    equity_multiple: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    avg_cash_on_cash: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    project_duration_years: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    exit_cap_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    yield_on_cost: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    deal: Mapped["Deal"] = relationship("Deal", back_populates="underwriting")
    source_document: Mapped["DealDocument"] = relationship("DealDocument")
