from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict


class FundBase(BaseModel):
    name: str
    strategy: str | None = None
    target_irr: Decimal | None = None
    target_equity_multiple: Decimal | None = None
    target_geography: str | None = None
    target_asset_types: str | None = None
    fund_size: Decimal | None = None
    gp_commitment: Decimal | None = None
    management_fee: Decimal | None = None
    carried_interest: Decimal | None = None
    preferred_return: Decimal | None = None
    status: str = "Active"
    details_json: dict[str, Any] | None = None


class FundCreate(FundBase):
    operator_id: UUID


class FundUpdate(BaseModel):
    name: str | None = None
    strategy: str | None = None
    target_irr: Decimal | None = None
    target_equity_multiple: Decimal | None = None
    target_geography: str | None = None
    target_asset_types: str | None = None
    fund_size: Decimal | None = None
    gp_commitment: Decimal | None = None
    management_fee: Decimal | None = None
    carried_interest: Decimal | None = None
    preferred_return: Decimal | None = None
    status: str | None = None
    details_json: dict[str, Any] | None = None


class FundResponse(FundBase):
    id: UUID
    operator_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
