from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.tool_definition import ToolDefinition
from app.schemas.tool import ToolDefinitionCreate, ToolDefinitionUpdate, ToolDefinitionResponse

router = APIRouter()


@router.get("", response_model=list[ToolDefinitionResponse])
async def list_tools(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ToolDefinition).order_by(ToolDefinition.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{tool_id}", response_model=ToolDefinitionResponse)
async def get_tool(tool_id: UUID, db: AsyncSession = Depends(get_db)):
    tool = await db.get(ToolDefinition, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.post("", response_model=ToolDefinitionResponse, status_code=201)
async def create_tool(data: ToolDefinitionCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(ToolDefinition).where(ToolDefinition.name == data.name)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Tool with this name already exists")
    tool = ToolDefinition(**data.model_dump())
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


@router.put("/{tool_id}", response_model=ToolDefinitionResponse)
async def update_tool(tool_id: UUID, data: ToolDefinitionUpdate, db: AsyncSession = Depends(get_db)):
    tool = await db.get(ToolDefinition, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tool, key, value)
    await db.commit()
    await db.refresh(tool)
    return tool


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(tool_id: UUID, db: AsyncSession = Depends(get_db)):
    tool = await db.get(ToolDefinition, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    await db.delete(tool)
    await db.commit()
