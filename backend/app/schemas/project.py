from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    genre: str
    style: str
    world_setting: str = ""
    characters: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    world_setting: Optional[str] = None
    characters: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    genre: str
    style: str
    world_setting: str
    characters: str
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    size: int
