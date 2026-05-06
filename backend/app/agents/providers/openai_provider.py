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

    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> GenerateResult:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
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
        )

    async def stream_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
