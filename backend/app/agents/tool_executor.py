import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.tool_definition import ToolDefinition

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, tool_definitions: list[ToolDefinition], db=None, project_id: str = None):
        self.tools: dict[str, ToolDefinition] = {t.name: t for t in tool_definitions}
        self.db = db
        self.project_id = project_id
        self._builtin_implementations = {
            "web_search": self._web_search,
            "knowledge_query": self._knowledge_query,
            "time_query": self._time_query,
        }

    async def execute(self, tool_name: str, arguments: dict) -> str:
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found"
        tool_def = self.tools[tool_name]
        if tool_def.implementation_type == "builtin" and tool_name in self._builtin_implementations:
            try:
                result = await self._builtin_implementations[tool_name](**arguments)
                return result
            except Exception as e:
                logger.error(f"Tool '{tool_name}' execution failed: {e}")
                return f"Error executing tool '{tool_name}': {str(e)}"
        elif tool_def.implementation_type == "custom":
            return await self._execute_custom_tool(tool_def, arguments)
        return f"Error: No implementation for tool '{tool_name}'"

    async def _web_search(self, query: str, **kwargs) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1},
                )
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    abstract = data.get("Abstract", "")
                    if abstract:
                        results.append(abstract)
                    related = data.get("RelatedTopics", [])
                    for topic in related[:5]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            results.append(topic["Text"])
                    if results:
                        return "\n".join(results)
                return f"No search results found for: {query}"
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return f"Web search unavailable: {str(e)}"

    async def _knowledge_query(self, query: str, **kwargs) -> str:
        if not self.db or not self.project_id:
            return "Knowledge query unavailable: no database or project context"
        try:
            from app.services.memory_service import MemoryService
            import uuid
            memory_service = MemoryService(self.db)
            memories = await memory_service.search_memories(
                project_id=uuid.UUID(self.project_id),
                query=query,
                top_k=5,
            )
            if not memories:
                return "No relevant knowledge found"
            results = []
            for m in memories:
                results.append(f"[{m.category}] {m.content}")
            return "\n".join(results)
        except Exception as e:
            logger.warning(f"Knowledge query failed: {e}")
            return f"Knowledge query error: {str(e)}"

    async def _time_query(self, timezone_name: str = "UTC", **kwargs) -> str:
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(timezone_name)
            now = datetime.now(tz)
            return now.strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            now = datetime.now(timezone.utc)
            return now.strftime("%Y-%m-%d %H:%M:%S UTC")

    async def _execute_custom_tool(self, tool_def: ToolDefinition, arguments: dict) -> str:
        config = tool_def.implementation_config or {}
        url = config.get("url")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        if not url:
            return f"Error: Custom tool '{tool_def.name}' has no URL configured"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, params=arguments, headers=headers)
                else:
                    response = await client.post(url, json=arguments, headers=headers)
                if response.status_code == 200:
                    return response.text[:2000]
                return f"Error: Tool returned status {response.status_code}"
        except Exception as e:
            return f"Error calling custom tool: {str(e)}"

    def get_tools_for_llm(self) -> list[dict]:
        tools = []
        for name, tool_def in self.tools.items():
            if not tool_def.is_active:
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.parameters_schema or {"type": "object", "properties": {}},
                },
            })
        return tools
