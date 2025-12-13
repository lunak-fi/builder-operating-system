from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DealDocumentBase(BaseModel):
    deal_id: UUID | None = None
    document_type: str
    file_name: str
    file_url: str
    source_description: str | None = None
    parsed_text: str | None = None
    parsing_status: str = "pending"
    parsing_error: str | None = None


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


class DealDocumentResponse(DealDocumentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
