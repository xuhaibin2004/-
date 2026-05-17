import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_agent_platform"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_project(client):
    data = {
        "name": "测试项目",
        "genre": "科幻",
        "style": "轻松幽默",
        "world_setting": "未来世界",
        "characters": "主角A，配角B",
    }
    response = await client.post("/api/projects", json=data)
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == "测试项目"
    assert result["genre"] == "科幻"
    assert "id" in result


@pytest.mark.asyncio
async def test_list_projects(client):
    for i in range(3):
        await client.post("/api/projects", json={
            "name": f"项目{i}",
            "genre": "科幻",
            "style": "轻松",
        })
    response = await client.get("/api/projects")
    assert response.status_code == 200
    result = response.json()
    assert len(result["items"]) >= 3


@pytest.mark.asyncio
async def test_get_project(client):
    create_resp = await client.post("/api/projects", json={
        "name": "获取测试",
        "genre": "悬疑",
        "style": "严肃",
    })
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "获取测试"


@pytest.mark.asyncio
async def test_update_project(client):
    create_resp = await client.post("/api/projects", json={
        "name": "更新前",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    response = await client.put(f"/api/projects/{project_id}", json={"name": "更新后"})
    assert response.status_code == 200
    assert response.json()["name"] == "更新后"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_resp = await client.post("/api/projects", json={
        "name": "删除测试",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_agent(client):
    create_resp = await client.post("/api/projects", json={
        "name": "Agent测试项目",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    response = await client.post(f"/api/projects/{project_id}/agents", json={
        "name": "测试Agent",
        "prompt_template": "测试模板 {plot_summary}",
        "provider": "openai",
        "model": "gpt-4o-mini",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "测试Agent"


@pytest.mark.asyncio
async def test_list_agents(client):
    create_resp = await client.post("/api/projects", json={
        "name": "Agent列表项目",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    await client.post(f"/api/projects/{project_id}/agents", json={
        "name": "Agent1",
        "prompt_template": "模板1",
    })
    response = await client.get(f"/api/projects/{project_id}/agents")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_init_builtin_templates(client):
    create_resp = await client.post("/api/projects", json={
        "name": "模板项目",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    response = await client.post(f"/api/projects/{project_id}/agents/init-templates")
    assert response.status_code == 201
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_create_task(client):
    create_resp = await client.post("/api/projects", json={
        "name": "任务测试项目",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    with patch("app.api.tasks.redis_client") as mock_redis:
        mock_redis.xadd = AsyncMock()
        response = await client.post(f"/api/projects/{project_id}/tasks", json={
            "plot_summary": "主角在未来世界冒险",
            "agent_count": 3,
        })
    assert response.status_code == 201
    assert response.json()["plot_summary"] == "主角在未来世界冒险"


@pytest.mark.asyncio
async def test_get_task_status(client):
    create_resp = await client.post("/api/projects", json={
        "name": "状态测试项目",
        "genre": "科幻",
        "style": "轻松",
    })
    project_id = create_resp.json()["id"]
    with patch("app.api.tasks.redis_client") as mock_redis:
        mock_redis.xadd = AsyncMock()
        task_resp = await client.post(f"/api/projects/{project_id}/tasks", json={
            "plot_summary": "测试剧情",
        })
    task_id = task_resp.json()["id"]
    response = await client.get(f"/api/tasks/{task_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
