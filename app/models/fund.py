from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import uuid

from app.db.base import Base


class Fund(Base):
    __tablename__ = "funds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operators.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)  # SFR, Multifamily, Mixed, etc.

    # Target metrics
    target_irr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    target_equity_multiple: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    target_geography: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comma-separated or JSON
    target_asset_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comma-separated or JSON

    # Fund structure
    fund_size: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    gp_commitment: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    management_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)  # As decimal (0.02 = 2%)
    carried_interest: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)  # As decimal (0.20 = 20%)
    preferred_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)  # As decimal (0.08 = 8%)

    # Status
    status: Mapped[str] = mapped_column(Text, nullable=False, default="Active")  # Active, Closed, Fundraising

    # Flexible storage for additional data
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    operator: Mapped["Operator"] = relationship("Operator", back_populates="funds")
    deals: Mapped[list["Deal"]] = relationship("Deal", back_populates="fund")
    documents: Mapped[list["DealDocument"]] = relationship(
        "DealDocument", back_populates="fund", foreign_keys="DealDocument.fund_id"
    )
