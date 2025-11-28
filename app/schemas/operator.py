from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class OperatorBase(BaseModel):
    name: str
    legal_name: str | None = None
    website_url: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_country: str = "USA"
    primary_geography_focus: str | None = None
    primary_asset_type_focus: str | None = None
    description: str | None = None
    notes: str | None = None


class OperatorCreate(OperatorBase):
    pass


class OperatorUpdate(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    website_url: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_country: str | None = None
    primary_geography_focus: str | None = None
    primary_asset_type_focus: str | None = None
    description: str | None = None
    notes: str | None = None


class OperatorResponse(OperatorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
