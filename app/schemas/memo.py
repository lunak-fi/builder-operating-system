from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MemoBase(BaseModel):
    deal_id: UUID
    title: str | None = None
    memo_type: str = "investment_memo"
    content_markdown: str
    generated_by: str | None = None


class MemoCreate(MemoBase):
    pass


class MemoUpdate(BaseModel):
    deal_id: UUID | None = None
    title: str | None = None
    memo_type: str | None = None
    content_markdown: str | None = None
    generated_by: str | None = None


class MemoResponse(MemoBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
