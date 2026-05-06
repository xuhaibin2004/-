import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.generation_agent import GenerationAgent, GenerationOutput, create_diverse_agents
from app.agents.evaluation_agent import EvaluationAgent, EvaluationOutput
from app.agents.mcp_sandbox import MCPSandbox


def test_generation_agent_build_prompt():
    agent = GenerationAgent(
        name="TestAgent",
        prompt_template="剧情：{plot_summary}\n记忆：{memory_context}\n风格：{style}",
        role_description="测试角色",
    )
    prompt = agent.build_prompt(
        plot_summary="主角冒险",
        memory_context="避免空洞",
        style="轻松",
    )
    assert "主角冒险" in prompt
    assert "避免空洞" in prompt
    assert "轻松" in prompt
    assert "测试角色" in prompt


def test_create_diverse_agents():
    configs = [
        {"name": "A", "prompt_template": "t1", "temperature": 0.7},
        {"name": "B", "prompt_template": "t2", "temperature": 0.7},
        {"name": "C", "prompt_template": "t3", "temperature": 0.7},
    ]
    agents = create_diverse_agents(configs)
    assert len(agents) == 3
    temps = [a.temperature for a in agents]
    assert temps[0] < temps[1] < temps[2] or temps[0] != temps[1]


@pytest.mark.asyncio
async def test_generation_agent_timeout():
    agent = GenerationAgent(
        name="TimeoutAgent",
        prompt_template="test",
        timeout=1,
    )
    with patch("app.agents.generation_agent.provider_manager") as mock_pm:
        mock_pm.generate_with_fallback = AsyncMock(side_effect=TimeoutError())
        result = await agent.generate("test prompt")
    assert not result.success
    assert "timed out" in result.error_message or result.error_message


@pytest.mark.asyncio
async def test_evaluation_agent_parse_scores():
    agent = EvaluationAgent()
    json_content = '{"ai_rate_score": 65, "creativity_score": 80, "coherence_score": 75, "style_match_score": 70, "overall_score": 72, "analysis": "test"}'
    scores = agent._parse_scores(json_content)
    assert scores["ai_rate_score"] == 65.0
    assert scores["creativity_score"] == 80.0


@pytest.mark.asyncio
async def test_evaluation_agent_parse_scores_fallback():
    agent = EvaluationAgent()
    scores = agent._parse_scores("not json")
    assert scores["ai_rate_score"] == 50.0


def test_mcp_sandbox_allowed_tools():
    sandbox = MCPSandbox(allowed_tools=["web_search", "knowledge_query"])
    assert sandbox.is_tool_allowed("web_search")
    assert not sandbox.is_tool_allowed("file_read")
    assert len(sandbox.list_allowed_tools()) == 2


@pytest.mark.asyncio
async def test_mcp_sandbox_call_blocked():
    sandbox = MCPSandbox(allowed_tools=["web_search"])
    with pytest.raises(PermissionError):
        await sandbox.call_tool("file_read")
