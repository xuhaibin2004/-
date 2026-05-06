from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class GenerateResult:
    content: str
    model: str
    provider: str
    usage: dict = None


class LLMProvider(ABC):
    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> GenerateResult:
        pass

    @abstractmethod
    async def stream_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> AsyncIterator[str]:
        pass
