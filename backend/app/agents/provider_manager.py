import logging
from typing import AsyncIterator, Optional

from app.agents.providers.base import LLMProvider, GenerateResult
from app.agents.providers import create_provider
from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER_CONFIGS = {
    "openai": {
        "api_key": settings.OPENAI_API_KEY,
        "base_url": settings.OPENAI_BASE_URL or None,
        "models": ["gpt-4o", "gpt-4o-mini"],
    },
    "anthropic": {
        "api_key": settings.ANTHROPIC_API_KEY,
        "base_url": settings.ANTHROPIC_BASE_URL or None,
        "models": ["claude-sonnet-4-20250514"],
    },
}

FALLBACK_ORDER = ["openai", "anthropic"]


class ProviderManager:
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def get_provider(self, provider_name: str, model: str) -> LLMProvider:
        cache_key = f"{provider_name}:{model}"
        if cache_key not in self._providers:
            config = PROVIDER_CONFIGS.get(provider_name)
            if not config:
                raise ValueError(f"Unknown provider: {provider_name}")
            self._providers[cache_key] = create_provider(
                provider_name=provider_name,
                model=model,
                api_key=config["api_key"],
                base_url=config.get("base_url"),
            )
        return self._providers[cache_key]

    def get_provider_from_config(self, provider_type: str, model: str, api_key: str, base_url: str = "") -> LLMProvider:
        cache_key = f"cfg:{provider_type}:{model}:{hash(api_key)}"
        if cache_key not in self._providers:
            self._providers[cache_key] = create_provider(
                provider_name=provider_type,
                model=model,
                api_key=api_key,
                base_url=base_url or None,
            )
        return self._providers[cache_key]

    async def generate_with_fallback(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        providers_to_try = [provider_name]
        for fb in FALLBACK_ORDER:
            if fb != provider_name:
                providers_to_try.append(fb)

        last_error = None
        for prov_name in providers_to_try:
            config = PROVIDER_CONFIGS.get(prov_name)
            if not config or not config.get("api_key"):
                continue
            try:
                fb_model = model if prov_name == provider_name else config["models"][0]
                provider = self.get_provider(prov_name, fb_model)
                result = await provider.generate(prompt, temperature, max_tokens)
                if prov_name != provider_name:
                    logger.info(f"Failover: used {prov_name}/{fb_model} instead of {provider_name}/{model}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {prov_name} failed: {e}")
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    async def generate_from_config(
        self,
        provider_type: str,
        model: str,
        api_key: str,
        base_url: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        provider = self.get_provider_from_config(provider_type, model, api_key, base_url)
        return await provider.generate(prompt, temperature, max_tokens)

    async def stream_from_config(
        self,
        provider_type: str,
        model: str,
        api_key: str,
        base_url: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        provider = self.get_provider_from_config(provider_type, model, api_key, base_url)
        async for chunk in provider.stream_generate(prompt, temperature, max_tokens):
            yield chunk

    async def generate_with_tools_from_config(
        self,
        provider_type: str,
        model: str,
        api_key: str,
        base_url: str,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        provider = self.get_provider_from_config(provider_type, model, api_key, base_url)
        return await provider.generate_with_tools(prompt, tools, temperature, max_tokens)

    async def stream_with_tools_from_config(
        self,
        provider_type: str,
        model: str,
        api_key: str,
        base_url: str,
        prompt: str,
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        provider = self.get_provider_from_config(provider_type, model, api_key, base_url)
        async for event in provider.stream_generate_with_tools(prompt, tools, temperature, max_tokens):
            yield event

    def clear_cache(self):
        self._providers.clear()


provider_manager = ProviderManager()
