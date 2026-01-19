from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.operator import OperatorResponse


class DealBase(BaseModel):
    operator_id: UUID
    internal_code: str
    deal_name: str
    country: str = "USA"
    state: str | None = None
    msa: str | None = None
    submarket: str | None = None
    address_line1: str | None = None
    postal_code: str | None = None
    asset_type: str | None = None
    strategy_type: str | None = None
    num_units: int | None = None
    building_sf: Decimal | None = None
    year_built: int | None = None
    business_plan_summary: str | None = None
    hold_period_years: Decimal | None = None
    status: str = "inbox"
    operator_needs_review: bool = False


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    operator_id: UUID | None = None
    internal_code: str | None = None
    deal_name: str | None = None
    country: str | None = None
    state: str | None = None
    msa: str | None = None
    submarket: str | None = None
    address_line1: str | None = None
    postal_code: str | None = None
    asset_type: str | None = None
    strategy_type: str | None = None
    num_units: int | None = None
    building_sf: Decimal | None = None
    year_built: int | None = None
    business_plan_summary: str | None = None
    hold_period_years: Decimal | None = None
    status: str | None = None
    operator_needs_review: bool | None = None


class DealResponse(DealBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    operators: list["OperatorResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Resolve forward references
from app.schemas.operator import OperatorResponse
DealResponse.model_rebuild()
