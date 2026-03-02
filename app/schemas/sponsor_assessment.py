from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AssessmentDimension(BaseModel):
    signal: str  # 'strong', 'moderate', 'weak', 'tbd'
    notes: str = ""


class SponsorAssessmentUpsert(BaseModel):
    dimensions: dict[str, AssessmentDimension]


class SponsorAssessmentResponse(BaseModel):
    id: UUID
    operator_id: UUID
    dimensions: Optional[dict[str, AssessmentDimension]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
