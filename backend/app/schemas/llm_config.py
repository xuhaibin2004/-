from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class LLMConfigCreate(BaseModel):
    name: str
    provider_type: str
    api_key: str
    base_url: str = ""
    available_models: list[str] = []
    is_active: bool = True


class LLMConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    available_models: Optional[list[str]] = None
    is_active: Optional[bool] = None


class LLMConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    provider_type: str
    api_key: str
    base_url: str
    available_models: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LLMConfigBrief(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    provider_type: str
    available_models: list[str]
    is_active: bool


def mask_api_key(api_key: str) -> str:
    if not api_key or len(api_key) <= 8:
        return "***"
    return api_key[:4] + "***" + api_key[-4:]
