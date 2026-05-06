import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

from app.agents.generation_agent import GenerationOutput
from app.agents.evaluation_agent import EvaluationOutput
from app.services.task_scheduler import TaskScheduler


@pytest.mark.asyncio
async def test_scheduler_handles_missing_task():
    scheduler = TaskScheduler()
    with patch("app.services.task_scheduler.AsyncSessionLocal") as mock_session:
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_db.get = AsyncMock(return_value=None)
        await scheduler.run_task(uuid.uuid4())


@pytest.mark.asyncio
async def test_scheduler_handles_no_agents():
    scheduler = TaskScheduler()
    task_id = uuid.uuid4()
    project_id = uuid.uuid4()

    mock_task = MagicMock()
    mock_task.id = task_id
    mock_task.project_id = project_id
    mock_task.plot_summary = "test"
    mock_task.max_iterations = 3
    mock_task.iteration_count = 0
    mock_task.ai_rate_threshold = 70.0

    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.world_setting = ""
    mock_project.characters = ""
    mock_project.style = ""
    mock_project.genre = ""

    with patch("app.services.task_scheduler.AsyncSessionLocal") as mock_session:
        mock_db = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_db.get = AsyncMock(side_effect=lambda model, pk: mock_task if pk == task_id else mock_project if pk == project_id else None)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

        with patch("app.services.task_scheduler.publish_task_status", new_callable=AsyncMock):
            await scheduler.run_task(task_id)
