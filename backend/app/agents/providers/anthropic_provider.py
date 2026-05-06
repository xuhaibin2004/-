import json
from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from app.agents.providers.base import LLMProvider, GenerateResult


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = "", base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = AsyncAnthropic(**client_kwargs)

    def _convert_tools_to_anthropic(self, tools: list[dict]) -> list[dict]:
        anthropic_tools = []
        for tool in tools:
            func = tool.get("function", tool)
            anthropic_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    def _extract_tool_calls(self, content_blocks: list) -> list[dict]:
        tool_calls = []
        for block in content_blocks:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": json.dumps(block.input),
                })
        return tool_calls

    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> GenerateResult:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return GenerateResult(
            content=content,
            model=response.model,
            provider="anthropic",
            usage=usage,
            finish_reason=response.stop_reason or "",
        )

    async def stream_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        anthropic_tools = self._convert_tools_to_anthropic(tools)
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=anthropic_tools,
            temperature=temperature,
        )
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        tool_calls = self._extract_tool_calls(response.content)
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return GenerateResult(
            content=content,
            model=response.model,
            provider="anthropic",
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "",
        )

    async def stream_generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        anthropic_tools = self._convert_tools_to_anthropic(tools)
        tool_call_buffers: dict[str, dict] = {}
        current_tool_id = None
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=anthropic_tools,
            temperature=temperature,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield {"type": "content", "data": event.delta.text}
                    elif event.delta.type == "input_json_delta":
                        if current_tool_id and current_tool_id in tool_call_buffers:
                            tool_call_buffers[current_tool_id]["arguments"] += event.delta.partial_json
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool_id = event.content_block.id
                        tool_call_buffers[current_tool_id] = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": "",
                        }
                elif event.type == "message_stop":
                    for tid in tool_call_buffers:
                        yield {"type": "tool_call", "data": tool_call_buffers[tid]}
                    yield {"type": "done", "data": {"finish_reason": "stop"}}

    async def generate_with_messages(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                anthropic_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                anthropic_messages.append({"role": role, "content": content})

        system_text = ""
        for msg in messages:
            if msg.get("role") == "system":
                if isinstance(msg.get("content"), str):
                    system_text = msg["content"]
                break

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
            "temperature": temperature,
        }
        if system_text:
            kwargs["system"] = system_text
        if tools:
            kwargs["tools"] = self._convert_tools_to_anthropic(tools)

        response = await self.client.messages.create(**kwargs)
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        tool_calls = self._extract_tool_calls(response.content)
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return GenerateResult(
            content=content,
            model=response.model,
            provider="anthropic",
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "",
        )
