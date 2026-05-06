from typing import Optional

from app.agents.providers.openai_provider import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    def __init__(self, model: str = "", api_key: str = "", base_url: str = ""):
        if not base_url:
            raise ValueError("base_url is required for OpenAI compatible provider")
        super().__init__(model=model, api_key=api_key, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return "openai_compatible"
