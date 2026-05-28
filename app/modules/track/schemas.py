from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TrackEventIn(BaseModel):
    eventName: str = Field(..., min_length=2, max_length=80)
    pageUrl: str = Field(..., max_length=500)
    targetType: Optional[str] = Field(default=None, max_length=50)
    targetId: Optional[str] = Field(default=None, max_length=100)
    extra: Dict[str, Any] = Field(default_factory=dict)
