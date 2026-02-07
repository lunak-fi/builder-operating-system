from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class DealNoteBase(BaseModel):
    deal_id: UUID
    author_name: str | None = None
    note_type: str  # 'quick_note', 'thread_summary'
    content: str
    metadata_json: dict[str, Any] | None = None


class DealNoteCreate(BaseModel):
    """Schema for creating a note - deal_id passed separately"""
    author_name: str | None = None
    note_type: str = "quick_note"
    content: str
    metadata_json: dict[str, Any] | None = None


class DealNoteUpdate(BaseModel):
    author_name: str | None = None
    content: str | None = None
    metadata_json: dict[str, Any] | None = None


class DealNoteResponse(DealNoteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadExtractionRequest(BaseModel):
    """Request to extract insights from a text thread"""
    deal_id: UUID
    thread_content: str
    author_name: str | None = None


class ThreadExtractionResponse(BaseModel):
    """Response with extracted insights from a text thread"""
    note: DealNoteResponse
    insights: dict[str, Any]  # AI-extracted insights
