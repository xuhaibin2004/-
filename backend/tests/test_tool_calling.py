import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.tool_executor import ToolExecutor
from app.agents.tool_calling_loop import run_with_tools
from app.agents.providers.base import GenerateResult
from app.models.tool_definition import ToolDefinition


def _make_tool_def(name="web_search", description="search web", params=None, impl_type="builtin"):
    td = MagicMock(spec=ToolDefinition)
    td.name = name
    td.description = description
    td.parameters_schema = params or {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "search query"}},
        "required": ["query"],
    }
    td.implementation_type = impl_type
    td.implementation_config = {}
    td.is_active = True
    return td


@pytest.mark.asyncio
async def test_tool_executor_builtin_web_search():
    td = _make_tool_def("web_search", "search the web")
    executor = ToolExecutor([td])
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Abstract": "Test result", "RelatedTopics": []}
        mock_get.return_value = mock_response
        result = await executor.execute("web_search", {"query": "test"})
        assert "Test result" in result


@pytest.mark.asyncio
async def test_tool_executor_time_query():
    td = _make_tool_def("time_query", "get current time", {"type": "object", "properties": {}})
    executor = ToolExecutor([td])
    result = await executor.execute("time_query", {})
    assert len(result) > 0


@pytest.mark.asyncio
async def test_tool_executor_unknown_tool():
    executor = ToolExecutor([])
    result = await executor.execute("nonexistent", {})
    assert "not found" in result


@pytest.mark.asyncio
async def test_get_tools_for_llm():
    td = _make_tool_def("web_search", "search the web")
    executor = ToolExecutor([td])
    tools = executor.get_tools_for_llm()
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "web_search"


@pytest.mark.asyncio
async def test_get_tools_for_llm_inactive():
    td = _make_tool_def("web_search", "search the web")
    td.is_active = False
    executor = ToolExecutor([td])
    tools = executor.get_tools_for_llm()
    assert len(tools) == 0


@pytest.mark.asyncio
async def test_tool_calling_loop_no_tool_calls():
    mock_provider = AsyncMock()
    mock_provider.generate_with_tools = AsyncMock(return_value=GenerateResult(
        content="Final answer",
        model="gpt-4o",
        provider="openai",
        usage={},
        tool_calls=[],
        finish_reason="stop",
    ))
    mock_provider.generate_with_messages = AsyncMock(return_value=GenerateResult(
        content="Final answer",
        model="gpt-4o",
        provider="openai",
        usage={},
        tool_calls=[],
        finish_reason="stop",
    ))

    td = _make_tool_def("web_search")
    executor = ToolExecutor([td])
    tools = executor.get_tools_for_llm()

    result = await run_with_tools(
        provider=mock_provider,
        prompt="test prompt",
        tools=tools,
        tool_executor=executor,
    )
    assert result.content == "Final answer"
    assert len(result.tool_calls) == 0


@pytest.mark.asyncio
async def test_tool_calling_loop_with_tool_calls():
    call_count = 0

    async def mock_generate_with_messages(messages, tools, temperature, max_tokens):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return GenerateResult(
                content="",
                model="gpt-4o",
                provider="openai",
                usage={},
                tool_calls=[{"id": "call_1", "name": "web_search", "arguments": '{"query": "test"}'}],
                finish_reason="tool_calls",
            )
        return GenerateResult(
            content="Based on search results...",
            model="gpt-4o",
            provider="openai",
            usage={},
            tool_calls=[],
            finish_reason="stop",
        )

    mock_provider = AsyncMock()
    mock_provider.generate_with_messages = mock_generate_with_messages
    mock_provider.provider = "openai"

    td = _make_tool_def("web_search")
    executor = ToolExecutor([td])
    with patch.object(executor, "execute", new_callable=AsyncMock, return_value="Search results here"):
        tools = executor.get_tools_for_llm()
        result = await run_with_tools(
            provider=mock_provider,
            prompt="search for something",
            tools=tools,
            tool_executor=executor,
        )
    assert "Based on search results" in result.content
