import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


async def inject_memory_to_prompt(
    db: AsyncSession,
    project_id: uuid.UUID,
    plot_summary: str,
    top_k: int = 5,
) -> str:
    memory_service = MemoryService(db)
    memories = await memory_service.search_memories(project_id, plot_summary, top_k=top_k)
    if not memories:
        return ""
    context_parts = []
    for m in memories:
        context_parts.append(f"[{m.category}] {m.content}")
    return "\n".join(context_parts)


async def write_negative_feedback_memory(
    db: AsyncSession,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    problem_types: list[str],
    description: str,
    confidence: float = 0.9,
):
    memory_service = MemoryService(db)
    problem_str = ", ".join(problem_types)
    content = f"问题类型: {problem_str}。描述: {description}"
    await memory_service.add_memory(
        project_id=project_id,
        content=content,
        category="negative_feedback",
        confidence=confidence,
        source_task_id=task_id,
    )


async def write_success_experience_memory(
    db: AsyncSession,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    ai_rate_score: float,
    overall_score: float,
    content_snippet: str,
    confidence: float = 0.8,
):
    memory_service = MemoryService(db)
    memory_content = f"成功经验: AI率={ai_rate_score:.1f}, 综合评分={overall_score:.1f}。内容片段: {content_snippet[:200]}"
    await memory_service.add_memory(
        project_id=project_id,
        content=memory_content,
        category="success_experience",
        confidence=confidence,
        source_task_id=task_id,
    )
