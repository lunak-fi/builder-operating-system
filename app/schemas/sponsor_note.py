from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class SponsorNoteBase(BaseModel):
    operator_id: UUID
    author_name: str | None = None
    note_type: str  # 'quick_note', 'meeting_log', 'call_log', 'email_summary'
    content: str
    interaction_date: datetime | None = None
    metadata_json: dict[str, Any] | None = None


class SponsorNoteCreate(BaseModel):
    """Schema for creating a sponsor note - operator_id passed separately"""
    author_name: str | None = None
    note_type: str = "quick_note"
    content: str
    interaction_date: datetime | None = None
    metadata_json: dict[str, Any] | None = None


class SponsorNoteUpdate(BaseModel):
    author_name: str | None = None
    content: str | None = None
    note_type: str | None = None
    interaction_date: datetime | None = None
    metadata_json: dict[str, Any] | None = None


class SponsorNoteResponse(SponsorNoteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
