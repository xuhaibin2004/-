import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_stream_endpoint_missing_params(client):
    response = await client.get("/api/stream/generate")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stream_endpoint_agent_not_found(client):
    response = await client.get(
        "/api/stream/generate",
        params={"agent_config_id": str(uuid4()), "prompt": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_endpoint_no_api_key(client, db_session):
    from app.models.agent_config import AgentConfig
    from app.models.project import Project

    project = Project(name="Stream Test Project", genre="fiction", style="literary")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    agent = AgentConfig(
        project_id=project.id,
        name="Stream Agent",
        prompt_template="Write about {plot_summary}",
        provider="openai",
        model="gpt-4o-mini",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    response = await client.get(
        "/api/stream/generate",
        params={"agent_config_id": str(agent.id), "prompt": "test"},
    )
    assert response.status_code == 400
