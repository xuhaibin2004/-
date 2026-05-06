from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class ScoreResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    generation_result_id: UUID
    ai_rate_score: float
    creativity_score: float
    coherence_score: float
    style_match_score: float
    overall_score: float
    external_ai_rate: Optional[float] = None
    scorer_type: str
    created_at: datetime


class GenerationResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    task_id: UUID
    agent_config_id: Optional[UUID] = None
    content: str
    status: str
    error_message: Optional[str] = None
    generation_time_ms: Optional[int] = None
    iteration: int
    is_edited: bool
    is_recommended: bool
    is_selected: bool
    created_at: datetime
    score: Optional[ScoreResultResponse] = None


class FeedbackRequest(BaseModel):
    problem_types: list[str]
    description: str


class ContentEditRequest(BaseModel):
    content: str


class FinalizeRequest(BaseModel):
    result_id: str
