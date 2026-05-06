import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.agent_config import AgentConfig
from app.models.llm_config import LLMProviderConfig
from app.models.tool_definition import ToolDefinition
from app.agents.provider_manager import provider_manager
from app.agents.tool_executor import ToolExecutor
from app.agents.tool_calling_loop import run_with_tools, stream_with_tools

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/generate")
async def stream_generate(
    agent_config_id: str = Query(...),
    prompt: str = Query(...),
    project_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    agent_config = await db.get(AgentConfig, uuid.UUID(agent_config_id))
    if not agent_config:
        raise HTTPException(status_code=404, detail="Agent config not found")

    llm_config = None
    if agent_config.llm_config_id:
        llm_config = await db.get(LLMProviderConfig, agent_config.llm_config_id)

    provider_type = llm_config.provider_type if llm_config else agent_config.provider
    model = agent_config.model
    api_key = llm_config.api_key if llm_config else ""
    base_url = llm_config.base_url if llm_config else ""

    if not api_key:
        raise HTTPException(status_code=400, detail="No API key configured")

    tool_defs = []
    if agent_config.tools:
        result = await db.execute(
            select(ToolDefinition).where(
                ToolDefinition.name.in_(agent_config.tools),
                ToolDefinition.is_active == True,
            )
        )
        tool_defs = list(result.scalars().all())

    tool_executor = ToolExecutor(tool_defs, db=db, project_id=project_id)

    async def event_stream():
        try:
            if tool_defs:
                tools = tool_executor.get_tools_for_llm()
                provider = provider_manager.get_provider_from_config(provider_type, model, api_key, base_url)
                async for event in stream_with_tools(
                    provider, prompt, tools, tool_executor,
                    temperature=agent_config.temperature,
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                async for chunk in provider_manager.stream_from_config(
                    provider_type, model, api_key, base_url,
                    prompt, temperature=agent_config.temperature,
                ):
                    yield f"data: {json.dumps({'type': 'content', 'data': chunk}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'data': {'finish_reason': 'stop'}})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
