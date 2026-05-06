from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_TOOLS = [
    "web_search",
    "knowledge_query",
]


class MCPSandbox:
    def __init__(self, allowed_tools: Optional[list[str]] = None):
        self.allowed_tools = set(allowed_tools or DEFAULT_ALLOWED_TOOLS)
        self._tool_registry: dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        if name in self.allowed_tools:
            self._tool_registry[name] = func

    async def call_tool(self, name: str, **kwargs) -> Any:
        if name not in self.allowed_tools:
            raise PermissionError(f"Tool '{name}' is not allowed in this sandbox")
        if name not in self._tool_registry:
            raise RuntimeError(f"Tool '{name}' is not registered")
        return await self._tool_registry[name](**kwargs)

    def is_tool_allowed(self, name: str) -> bool:
        return name in self.allowed_tools

    def list_allowed_tools(self) -> list[str]:
        return sorted(self.allowed_tools)
