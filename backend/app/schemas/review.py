from pydantic import BaseModel

from app.schemas.task import TaskResponse
from app.schemas.generation import GenerationResultResponse


class ReviewResponse(BaseModel):
    task: TaskResponse
    results: list[GenerationResultResponse]
    iteration_history: list[dict]
