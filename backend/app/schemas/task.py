from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    plot_summary: str
    agent_count: int = 3
    max_iterations: int = 3
    ai_rate_threshold: float = 70.0


class TaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    plot_summary: str
    status: str
    iteration_count: int
    max_iterations: int
    ai_rate_threshold: float
    agent_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    iteration_count: int
    agent_statuses: list[dict]


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    size: int
