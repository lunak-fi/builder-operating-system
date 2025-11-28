from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Any


class DealUnderwritingBase(BaseModel):
    deal_id: UUID
    source_document_id: UUID | None = None
    version_label: str | None = None
    total_project_cost: Decimal | None = None
    land_cost: Decimal | None = None
    hard_cost: Decimal | None = None
    soft_cost: Decimal | None = None
    loan_amount: Decimal | None = None
    equity_required: Decimal | None = None
    interest_rate: Decimal | None = None
    ltv: Decimal | None = None
    ltc: Decimal | None = None
    dscr_at_stabilization: Decimal | None = None
    levered_irr: Decimal | None = None
    unlevered_irr: Decimal | None = None
    equity_multiple: Decimal | None = None
    avg_cash_on_cash: Decimal | None = None
    project_duration_years: Decimal | None = None
    exit_cap_rate: Decimal | None = None
    yield_on_cost: Decimal | None = None
    details_json: dict[str, Any] | None = None


class DealUnderwritingCreate(DealUnderwritingBase):
    pass


class DealUnderwritingUpdate(BaseModel):
    deal_id: UUID | None = None
    source_document_id: UUID | None = None
    version_label: str | None = None
    total_project_cost: Decimal | None = None
    land_cost: Decimal | None = None
    hard_cost: Decimal | None = None
    soft_cost: Decimal | None = None
    loan_amount: Decimal | None = None
    equity_required: Decimal | None = None
    interest_rate: Decimal | None = None
    ltv: Decimal | None = None
    ltc: Decimal | None = None
    dscr_at_stabilization: Decimal | None = None
    levered_irr: Decimal | None = None
    unlevered_irr: Decimal | None = None
    equity_multiple: Decimal | None = None
    avg_cash_on_cash: Decimal | None = None
    project_duration_years: Decimal | None = None
    exit_cap_rate: Decimal | None = None
    yield_on_cost: Decimal | None = None
    details_json: dict[str, Any] | None = None


class DealUnderwritingResponse(DealUnderwritingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
