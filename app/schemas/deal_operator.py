from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.operator import OperatorResponse


class AddOperatorRequest(BaseModel):
    """Request to add an operator (sponsor) to a deal"""
    operator_id: UUID
    is_primary: bool = False


class UpdateOperatorRequest(BaseModel):
    """Request to update an operator's relationship to a deal"""
    is_primary: bool


class DealOperatorResponse(BaseModel):
    """Response containing operator details and their relationship to the deal"""
    id: UUID
    deal_id: UUID
    operator_id: UUID
    is_primary: bool
    created_at: datetime
    operator: "OperatorResponse"

    model_config = ConfigDict(from_attributes=True)


# Resolve forward references
from app.schemas.operator import OperatorResponse
DealOperatorResponse.model_rebuild()
