from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    prompt_template: str
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    role_description: str = ""


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    prompt_template: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    role_description: Optional[str] = None


class AgentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    project_id: UUID
    name: str
    prompt_template: str
    provider: str
    model: str
    temperature: float
    role_description: str
    is_builtin: bool
    created_at: datetime
