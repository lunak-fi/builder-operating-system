from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types"""
    OFFER_MEMO = "offer_memo"
    FINANCIAL_MODEL = "financial_model"
    TRANSCRIPT = "transcript"
    EMAIL = "email"
    OTHER = "other"


class DealDocumentBase(BaseModel):
    deal_id: UUID | None = None
    document_type: str
    file_name: str
    file_url: str
    source_description: str | None = None
    parsed_text: str | None = None
    parsing_status: str = "pending"
    parsing_error: str | None = None
    file_size: int | None = None
    metadata_json: dict | None = None
    parent_document_id: UUID | None = None
    version_number: int = 1


class DealDocumentCreate(DealDocumentBase):
    pass


class DealDocumentUpdate(BaseModel):
    deal_id: UUID | None = None
    document_type: str | None = None
    file_name: str | None = None
    file_url: str | None = None
    source_description: str | None = None
    parsed_text: str | None = None
    parsing_status: str | None = None
    parsing_error: str | None = None
    file_size: int | None = None
    metadata_json: dict | None = None
    parent_document_id: UUID | None = None
    version_number: int | None = None


class DealDocumentResponse(DealDocumentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
