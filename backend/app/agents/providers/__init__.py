from app.agents.providers.base import LLMProvider, GenerateResult
from app.agents.providers.openai_provider import OpenAIProvider
from app.agents.providers.anthropic_provider import AnthropicProvider

PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def create_provider(provider_name: str, model: str, api_key: str, base_url: str = None) -> LLMProvider:
    cls = PROVIDER_REGISTRY.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(model=model, api_key=api_key, base_url=base_url)
