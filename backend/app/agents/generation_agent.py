import asyncio
import time
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from app.agents.provider_manager import provider_manager
from app.agents.tool_executor import ToolExecutor
from app.agents.tool_calling_loop import run_with_tools, stream_with_tools
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GenerationOutput:
    content: str
    agent_name: str
    provider: str
    model: str
    generation_time_ms: int
    error_message: Optional[str] = None
    success: bool = True


class GenerationAgent:
    def __init__(
        self,
        name: str,
        prompt_template: str,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        role_description: str = "",
        timeout: int = None,
        llm_config_id: str = None,
        api_key: str = "",
        base_url: str = "",
        tools: list[str] = None,
        tool_definitions: list = None,
        enable_streaming: bool = False,
        db=None,
        project_id: str = None,
    ):
        self.name = name
        self.prompt_template = prompt_template
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.role_description = role_description
        self.timeout = timeout or settings.DEFAULT_AGENT_TIMEOUT
        self.llm_config_id = llm_config_id
        self.api_key = api_key
        self.base_url = base_url
        self.tools = tools or []
        self.tool_definitions = tool_definitions or []
        self.enable_streaming = enable_streaming
        self.db = db
        self.project_id = project_id

    def build_prompt(
        self,
        plot_summary: str,
        memory_context: str = "",
        world_setting: str = "",
        characters: str = "",
        style: str = "",
        genre: str = "",
        feedback: str = "",
    ) -> str:
        prompt = self.prompt_template
        prompt = prompt.replace("{plot_summary}", plot_summary)
        prompt = prompt.replace("{memory_context}", memory_context or "暂无相关经验")
        prompt = prompt.replace("{world_setting}", world_setting or "无特定世界观设定")
        prompt = prompt.replace("{characters}", characters or "无特定角色设定")
        prompt = prompt.replace("{style}", style or "无特定风格要求")
        prompt = prompt.replace("{genre}", genre or "无特定题材要求")
        prompt = prompt.replace("{feedback}", feedback or "")
        if self.role_description:
            prompt = f"[角色设定] {self.role_description}\n\n{prompt}"
        return prompt

    async def generate(self, prompt: str) -> GenerationOutput:
        start_time = time.time()
        try:
            if self.tools and self.tool_definitions:
                result = await asyncio.wait_for(
                    self._generate_with_tools(prompt),
                    timeout=self.timeout,
                )
            elif self.api_key:
                result = await asyncio.wait_for(
                    provider_manager.generate_from_config(
                        provider_type=self.provider,
                        model=self.model,
                        api_key=self.api_key,
                        base_url=self.base_url,
                        prompt=prompt,
                        temperature=self.temperature,
                    ),
                    timeout=self.timeout,
                )
            else:
                result = await asyncio.wait_for(
                    provider_manager.generate_with_fallback(
                        provider_name=self.provider,
                        model=self.model,
                        prompt=prompt,
                        temperature=self.temperature,
                    ),
                    timeout=self.timeout,
                )
            elapsed_ms = int((time.time() - start_time) * 1000)
            return GenerationOutput(
                content=result.content,
                agent_name=self.name,
                provider=result.provider,
                model=result.model,
                generation_time_ms=elapsed_ms,
            )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return GenerationOutput(
                content="",
                agent_name=self.name,
                provider=self.provider,
                model=self.model,
                generation_time_ms=elapsed_ms,
                error_message=f"Agent timed out after {self.timeout}s",
                success=False,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return GenerationOutput(
                content="",
                agent_name=self.name,
                provider=self.provider,
                model=self.model,
                generation_time_ms=elapsed_ms,
                error_message=str(e),
                success=False,
            )

    async def _generate_with_tools(self, prompt: str):
        tool_executor = ToolExecutor(
            self.tool_definitions, db=self.db, project_id=self.project_id
        )
        tools_for_llm = tool_executor.get_tools_for_llm()
        if self.api_key:
            provider = provider_manager.get_provider_from_config(
                self.provider, self.model, self.api_key, self.base_url
            )
        else:
            provider = provider_manager.get_provider(self.provider, self.model)
        return await run_with_tools(
            provider=provider,
            prompt=prompt,
            tools=tools_for_llm,
            tool_executor=tool_executor,
            temperature=self.temperature,
        )

    async def generate_stream(self, prompt: str) -> AsyncIterator[dict]:
        try:
            if self.tools and self.tool_definitions:
                tool_executor = ToolExecutor(
                    self.tool_definitions, db=self.db, project_id=self.project_id
                )
                tools_for_llm = tool_executor.get_tools_for_llm()
                if self.api_key:
                    provider = provider_manager.get_provider_from_config(
                        self.provider, self.model, self.api_key, self.base_url
                    )
                else:
                    provider = provider_manager.get_provider(self.provider, self.model)
                async for event in stream_with_tools(
                    provider=provider,
                    prompt=prompt,
                    tools=tools_for_llm,
                    tool_executor=tool_executor,
                    temperature=self.temperature,
                ):
                    yield event
            elif self.api_key:
                async for chunk in provider_manager.stream_from_config(
                    provider_type=self.provider,
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    prompt=prompt,
                    temperature=self.temperature,
                ):
                    yield {"type": "content", "data": chunk}
                yield {"type": "done", "data": {"finish_reason": "stop"}}
            else:
                provider = provider_manager.get_provider(self.provider, self.model)
                async for chunk in provider.stream_generate(
                    prompt, temperature=self.temperature
                ):
                    yield {"type": "content", "data": chunk}
                yield {"type": "done", "data": {"finish_reason": "stop"}}
        except Exception as e:
            yield {"type": "error", "data": str(e)}


def create_diverse_agents(
    agent_configs: list[dict],
    diversity_factor: float = 0.15,
) -> list[GenerationAgent]:
    agents = []
    for i, config in enumerate(agent_configs):
        temp_offset = diversity_factor * (i - len(agent_configs) // 2)
        adjusted_temp = max(0.1, min(2.0, config.get("temperature", 0.7) + temp_offset))
        agent = GenerationAgent(
            name=config.get("name", f"Agent-{i+1}"),
            prompt_template=config.get("prompt_template", ""),
            provider=config.get("provider", "openai"),
            model=config.get("model", "gpt-4o-mini"),
            temperature=adjusted_temp,
            role_description=config.get("role_description", ""),
            llm_config_id=config.get("llm_config_id"),
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", ""),
            tools=config.get("tools", []),
            tool_definitions=config.get("tool_definitions", []),
            enable_streaming=config.get("enable_streaming", False),
            db=config.get("db"),
            project_id=config.get("project_id"),
        )
        agents.append(agent)
    return agents
