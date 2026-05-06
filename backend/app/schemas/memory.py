from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class MemoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    content: str
    category: str
    confidence: float
    source_task_id: Optional[UUID] = None
    is_expired: bool
    created_at: datetime
    expired_at: datetime
