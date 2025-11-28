from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PrincipalBase(BaseModel):
    operator_id: UUID
    full_name: str
    headline: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    phone: str | None = None
    bio: str | None = None
    background_summary: str | None = None
    years_experience: int | None = None


class PrincipalCreate(PrincipalBase):
    pass


class PrincipalUpdate(BaseModel):
    operator_id: UUID | None = None
    full_name: str | None = None
    headline: str | None = None
    linkedin_url: str | None = None
    email: str | None = None
    phone: str | None = None
    bio: str | None = None
    background_summary: str | None = None
    years_experience: int | None = None


class PrincipalResponse(PrincipalBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
