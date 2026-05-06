from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.redis import redis_client, STREAM_KEY
from app.models.task import Task
from app.models.project import Project
from app.models.generation_result import GenerationResult
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusResponse, TaskListResponse

router = APIRouter()


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(project_id: UUID, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    task = Task(project_id=project_id, **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await redis_client.xadd(STREAM_KEY, {"task_id": str(task.id), "project_id": str(project_id)})
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/projects/{project_id}/tasks", response_model=TaskListResponse)
async def list_tasks(project_id: UUID, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).where(Task.project_id == project_id))
    result = await db.execute(
        select(Task).where(Task.project_id == project_id).offset((page - 1) * size).limit(size).order_by(Task.created_at.desc())
    )
    items = list(result.scalars().all())
    return TaskListResponse(items=items, total=total, page=page, size=size)


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await db.execute(
        select(GenerationResult).where(GenerationResult.task_id == task_id)
    )
    gen_results = list(result.scalars().all())
    agent_statuses = []
    for gr in gen_results:
        agent_statuses.append({
            "agent_config_id": str(gr.agent_config_id) if gr.agent_config_id else None,
            "status": gr.status,
            "iteration": gr.iteration,
        })
    return TaskStatusResponse(task_id=task.id, status=task.status, iteration_count=task.iteration_count, agent_statuses=agent_statuses)
