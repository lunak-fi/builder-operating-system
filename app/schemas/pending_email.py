"""
Pydantic schemas for pending emails API.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum


class PendingEmailStatus(str, Enum):
    """Possible statuses for pending emails"""
    RECEIVED = "received"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class PendingEmailAttachmentResponse(BaseModel):
    """Response schema for pending email attachments"""
    id: UUID
    pending_email_id: UUID
    file_name: str
    content_type: str
    file_size: int
    storage_url: str
    parsing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PendingEmailBase(BaseModel):
    """Base schema for pending emails"""
    organization_id: str
    status: str = "received"
    from_address: str
    from_name: Optional[str] = None
    subject: str
    body_text: Optional[str] = None


class PendingEmailResponse(BaseModel):
    """Response schema for pending emails"""
    id: UUID
    organization_id: str
    status: str
    from_address: str
    from_name: Optional[str] = None
    subject: str
    body_text: Optional[str] = None
    raw_email_url: Optional[str] = None
    extracted_data: Optional[dict] = None
    operator_matches: Optional[list] = None
    error_message: Optional[str] = None
    deal_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    attachments: list[PendingEmailAttachmentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PendingEmailListResponse(BaseModel):
    """Simplified response for list view (without full extracted data)"""
    id: UUID
    organization_id: str
    status: str
    from_address: str
    from_name: Optional[str] = None
    subject: str
    extracted_data: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    attachments: list[PendingEmailAttachmentResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PendingEmailConfirmRequest(BaseModel):
    """Request to confirm a pending email and create/link a deal"""
    operator_ids: list[str]
    extracted_data: Optional[dict] = None  # Allow user to modify extracted data
    deal_id: Optional[str] = None  # If provided, link to existing deal instead of creating new


class PendingEmailConfirmResponse(BaseModel):
    """Response after confirming a pending email"""
    success: bool
    deal_id: str
    pending_email_id: str
    message: str = "Deal created successfully"


class PendingEmailCountResponse(BaseModel):
    """Response for pending email count (for inbox badge)"""
    count: int
