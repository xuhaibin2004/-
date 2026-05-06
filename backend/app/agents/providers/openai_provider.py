import json
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from app.agents.providers.base import LLMProvider, GenerateResult


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o", api_key: str = "", base_url: Optional[str] = None):
        super().__init__(model, api_key, base_url)
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = AsyncOpenAI(**client_kwargs)

    def _build_messages(self, prompt: str) -> list[dict]:
        return [{"role": "user", "content": prompt}]

    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> GenerateResult:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return GenerateResult(
            content=choice.message.content or "",
            model=response.model,
            provider="openai",
            usage=usage,
            finish_reason=choice.finish_reason or "",
        )

    async def stream_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt),
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        message = choice.message
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return GenerateResult(
            content=message.content or "",
            model=response.model,
            provider="openai",
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "",
        )

    async def stream_generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(prompt),
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        tool_call_buffers: dict[int, dict] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "content", "data": delta.content}
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc_delta.id:
                        tool_call_buffers[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_call_buffers[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_call_buffers[idx]["arguments"] += tc_delta.function.arguments
            if chunk.choices[0].finish_reason:
                for idx in sorted(tool_call_buffers.keys()):
                    yield {"type": "tool_call", "data": tool_call_buffers[idx]}
                yield {"type": "done", "data": {"finish_reason": chunk.choices[0].finish_reason}}

    async def generate_with_messages(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return GenerateResult(
            content=message.content or "",
            model=response.model,
            provider="openai",
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "",
        )
