import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ToolDefinitionCreate(BaseModel):
    name: str
    description: str = ""
    parameters_schema: dict = {"type": "object", "properties": {}}
    implementation_type: str = "builtin"
    implementation_config: dict = {}
    is_active: bool = True


class ToolDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters_schema: Optional[dict] = None
    implementation_type: Optional[str] = None
    implementation_config: Optional[dict] = None
    is_active: Optional[bool] = None


class ToolDefinitionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str
    parameters_schema: dict
    implementation_type: str
    implementation_config: dict
    is_active: bool
    created_at: datetime
