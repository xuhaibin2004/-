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
