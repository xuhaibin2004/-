import json
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.task import Task
from app.models.project import Project
from app.models.generation_result import GenerationResult
from app.models.score_result import ScoreResult
from app.schemas.generation import ContentEditRequest, FeedbackRequest, FinalizeRequest
from app.schemas.review import ReviewResponse
from app.schemas.generation import GenerationResultResponse, ScoreResultResponse
from app.schemas.task import TaskResponse
from app.services.memory_service import MemoryService
from app.agents.evaluation_agent import EvaluationAgent

router = APIRouter()


@router.get("/tasks/{task_id}/review", response_model=ReviewResponse)
async def get_review_data(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(
        select(GenerationResult)
        .where(GenerationResult.task_id == task_id)
        .options(selectinload(GenerationResult.score_results))
        .order_by(GenerationResult.iteration, GenerationResult.created_at)
    )
    gen_results = list(result.scalars().all())

    gen_responses = []
    for gr in gen_results:
        scores = [
            ScoreResultResponse.model_validate(s, from_attributes=True)
            for s in gr.score_results
        ]
        gen_resp = GenerationResultResponse(
            id=gr.id,
            task_id=gr.task_id,
            agent_config_id=gr.agent_config_id,
            content=gr.content,
            status=gr.status,
            error_message=gr.error_message,
            generation_time_ms=gr.generation_time_ms,
            iteration=gr.iteration,
            is_edited=gr.is_edited,
            is_recommended=gr.is_recommended,
            is_selected=gr.is_selected,
            created_at=gr.created_at,
            score=scores[0] if scores else None,
        )
        gen_responses.append(gen_resp)

    iteration_history = []
    iterations = {}
    for gr in gen_responses:
        if gr.iteration not in iterations:
            iterations[gr.iteration] = []
        iterations[gr.iteration].append({
            "id": str(gr.id),
            "status": gr.status,
            "ai_rate_score": gr.score.ai_rate_score if gr.score else None,
            "overall_score": gr.score.overall_score if gr.score else None,
        })
    for iter_num, results in sorted(iterations.items()):
        iteration_history.append({"iteration": iter_num, "results": results})

    task_resp = TaskResponse.model_validate(task, from_attributes=True)
    return ReviewResponse(task=task_resp, results=gen_responses, iteration_history=iteration_history)


@router.put("/generation-results/{result_id}")
async def edit_content(result_id: UUID, data: ContentEditRequest, db: AsyncSession = Depends(get_db)):
    gen_result = await db.get(GenerationResult, result_id)
    if not gen_result:
        raise HTTPException(status_code=404, detail="Generation result not found")
    gen_result.content = data.content
    gen_result.is_edited = True
    await db.commit()
    await db.refresh(gen_result)
    return {"message": "Content updated", "is_edited": True}


@router.post("/generation-results/{result_id}/recheck")
async def recheck_ai_rate(result_id: UUID, db: AsyncSession = Depends(get_db)):
    gen_result = await db.get(GenerationResult, result_id)
    if not gen_result:
        raise HTTPException(status_code=404, detail="Generation result not found")
    if not gen_result.content:
        raise HTTPException(status_code=400, detail="No content to check")

    task = await db.get(Task, gen_result.task_id)
    project = await db.get(Project, task.project_id) if task else None

    eval_agent = EvaluationAgent()
    eval_output = await eval_agent.evaluate(
        content=gen_result.content,
        style=project.style if project else "",
        genre=project.genre if project else "",
        world_setting=project.world_setting if project else "",
    )

    score = ScoreResult(
        generation_result_id=gen_result.id,
        ai_rate_score=eval_output.ai_rate_score,
        creativity_score=eval_output.creativity_score,
        coherence_score=eval_output.coherence_score,
        style_match_score=eval_output.style_match_score,
        overall_score=eval_output.overall_score,
        external_ai_rate=eval_output.external_ai_rate,
        scorer_type="llm_recheck",
    )
    db.add(score)
    await db.commit()
    await db.refresh(score)

    return {
        "ai_rate_score": score.ai_rate_score,
        "creativity_score": score.creativity_score,
        "coherence_score": score.coherence_score,
        "style_match_score": score.style_match_score,
        "overall_score": score.overall_score,
        "external_ai_rate": score.external_ai_rate,
    }


@router.post("/generation-results/{result_id}/feedback")
async def submit_feedback(result_id: UUID, data: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    gen_result = await db.get(GenerationResult, result_id)
    if not gen_result:
        raise HTTPException(status_code=404, detail="Generation result not found")

    task = await db.get(Task, gen_result.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    memory_service = MemoryService(db)
    problem_types_str = ", ".join(data.problem_types)
    memory_content = f"问题类型: {problem_types_str}。描述: {data.description}"
    await memory_service.add_memory(
        project_id=task.project_id,
        content=memory_content,
        category="negative_feedback",
        confidence=0.9,
        source_task_id=task.id,
    )

    return {"message": "Feedback saved to memory"}


@router.post("/tasks/{task_id}/finalize")
async def finalize_task(task_id: UUID, data: FinalizeRequest, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    gen_result = await db.get(GenerationResult, UUID(data.result_id))
    if not gen_result or gen_result.task_id != task_id:
        raise HTTPException(status_code=404, detail="Generation result not found")

    gen_result.is_selected = True
    task.status = "completed"
    task.completed_at = datetime.utcnow()

    if gen_result.score_results:
        best_score = gen_result.score_results[0]
        memory_service = MemoryService(db)
        await memory_service.add_memory(
            project_id=task.project_id,
            content=f"成功经验: AI率={best_score.ai_rate_score:.1f}, 综合评分={best_score.overall_score:.1f}。内容片段: {gen_result.content[:200]}",
            category="success_experience",
            confidence=0.8,
            source_task_id=task.id,
        )

    await db.commit()
    return {"message": "Task finalized", "task_id": str(task_id), "selected_result_id": data.result_id}
