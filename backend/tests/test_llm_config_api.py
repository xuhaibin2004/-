import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.schemas.llm_config import mask_api_key


@pytest.mark.asyncio
async def test_create_llm_config(client, db_session):
    data = {
        "name": "Test OpenAI",
        "provider_type": "openai",
        "api_key": "sk-test1234567890abcdef",
        "available_models": ["gpt-4o", "gpt-4o-mini"],
        "is_active": True,
    }
    response = await client.post("/api/llm-configs", json=data)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test OpenAI"
    assert body["provider_type"] == "openai"
    assert "sk-te***cdef" == body["api_key"]
    assert "gpt-4o" in body["available_models"]


@pytest.mark.asyncio
async def test_list_llm_configs(client, db_session):
    data = {
        "name": "Test Anthropic",
        "provider_type": "anthropic",
        "api_key": "sk-ant-test12345678",
        "available_models": ["claude-sonnet-4-20250514"],
    }
    await client.post("/api/llm-configs", json=data)
    response = await client.get("/api/llm-configs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    for config in body:
        assert "***" in config["api_key"]


@pytest.mark.asyncio
async def test_update_llm_config(client, db_session):
    data = {
        "name": "Test Update",
        "provider_type": "openai",
        "api_key": "sk-test-key-12345678",
        "available_models": ["gpt-4o"],
    }
    create_resp = await client.post("/api/llm-configs", json=data)
    config_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/llm-configs/{config_id}", json={"name": "Updated Name"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_llm_config_preserves_key(client, db_session):
    data = {
        "name": "Key Preserve Test",
        "provider_type": "openai",
        "api_key": "sk-test-key-12345678",
        "available_models": ["gpt-4o"],
    }
    create_resp = await client.post("/api/llm-configs", json=data)
    config_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/llm-configs/{config_id}",
        json={"api_key": "sk-te***5678"},
    )
    assert update_resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_llm_config(client, db_session):
    data = {
        "name": "To Delete",
        "provider_type": "openai_compatible",
        "api_key": "test-key",
        "base_url": "https://api.example.com/v1",
        "available_models": ["model-1"],
    }
    create_resp = await client.post("/api/llm-configs", json=data)
    config_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/llm-configs/{config_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/llm-configs/{config_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_brief_list_only_active(client, db_session):
    await client.post("/api/llm-configs", json={
        "name": "Active Config",
        "provider_type": "openai",
        "api_key": "sk-test",
        "available_models": ["gpt-4o"],
        "is_active": True,
    })
    await client.post("/api/llm-configs", json={
        "name": "Inactive Config",
        "provider_type": "openai",
        "api_key": "sk-test2",
        "available_models": ["gpt-4o"],
        "is_active": False,
    })
    resp = await client.get("/api/llm-configs/brief")
    assert resp.status_code == 200
    for cfg in resp.json():
        assert cfg["is_active"] is True


def test_mask_api_key():
    assert mask_api_key("sk-test1234567890abcdef") == "sk-t***cdef"
    assert mask_api_key("short") == "***"
    assert mask_api_key("") == "***"
    assert mask_api_key("12345678") == "1234***5678"


@pytest.mark.asyncio
async def test_test_connection(client, db_session):
    data = {
        "name": "Test Connection",
        "provider_type": "openai",
        "api_key": "sk-fake-key",
        "available_models": ["gpt-4o"],
    }
    create_resp = await client.post("/api/llm-configs", json=data)
    config_id = create_resp.json()["id"]

    with patch("app.agents.provider_manager.provider_manager.generate_from_config", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = MagicMock(content="Hello", model="gpt-4o")
        test_resp = await client.post(f"/api/llm-configs/{config_id}/test")
        assert test_resp.status_code == 200
        body = test_resp.json()
        assert body["success"] is True
