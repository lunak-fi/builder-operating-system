from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import List


class ActivityItem(BaseModel):
    """Activity item in deal timeline"""
    id: str
    type: str  # "document_uploaded", "document_version_uploaded"
    timestamp: datetime
    data: dict


class ActivityFeedResponse(BaseModel):
    """Response for activity feed endpoint"""
    activities: List[ActivityItem]
