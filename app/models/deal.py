from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, Integer, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    fund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("funds.id", ondelete="SET NULL"), nullable=True
    )
    internal_code: Mapped[str] = mapped_column(Text, nullable=False)
    deal_name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False, default="USA")
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    msa: Mapped[str | None] = mapped_column(Text, nullable=True)
    submarket: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    building_sf: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hold_period_years: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="inbox")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    operator: Mapped["Operator"] = relationship("Operator", back_populates="deals")
    fund: Mapped["Fund"] = relationship("Fund", back_populates="deals")
    documents: Mapped[list["DealDocument"]] = relationship(
        "DealDocument", back_populates="deal", cascade="all, delete-orphan"
    )
    underwriting: Mapped["DealUnderwriting"] = relationship(
        "DealUnderwriting", back_populates="deal", uselist=False, cascade="all, delete-orphan"
    )
    memos: Mapped[list["Memo"]] = relationship(
        "Memo", back_populates="deal", cascade="all, delete-orphan"
    )
