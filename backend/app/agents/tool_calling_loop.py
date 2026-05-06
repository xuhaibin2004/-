import json
import logging
from typing import AsyncIterator, Optional

from app.agents.providers.base import LLMProvider, GenerateResult
from app.agents.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


async def run_with_tools(
    provider: LLMProvider,
    prompt: str,
    tools: list[dict],
    tool_executor: ToolExecutor,
    max_rounds: int = 5,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> GenerateResult:
    messages = [{"role": "user", "content": prompt}]
    all_content = ""
    total_usage = {}

    for round_num in range(max_rounds):
        result = await _call_llm_with_messages(provider, messages, tools, temperature, max_tokens)

        if result.usage:
            for k, v in result.usage.items():
                total_usage[k] = total_usage.get(k, 0) + v

        if not result.tool_calls:
            all_content += result.content
            return GenerateResult(
                content=all_content,
                model=result.model,
                provider=result.provider,
                usage=total_usage,
                finish_reason=result.finish_reason,
            )

        all_content += result.content + "\n" if result.content else ""

        if hasattr(provider, "generate_with_messages"):
            messages = _append_assistant_message(messages, result, provider)
        else:
            messages.append({"role": "assistant", "content": result.content or ""})
            for tc in result.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }],
                })

        for tc in result.tool_calls:
            tool_name = tc["name"]
            try:
                arguments = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
            except json.JSONDecodeError:
                arguments = {}
            tool_result = await tool_executor.execute(tool_name, arguments)
            if provider.provider == "anthropic":
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": tool_result,
                    }],
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })

    return GenerateResult(
        content=all_content,
        model=result.model,
        provider=result.provider,
        usage=total_usage,
        finish_reason="max_rounds_reached",
    )


async def stream_with_tools(
    provider: LLMProvider,
    prompt: str,
    tools: list[dict],
    tool_executor: ToolExecutor,
    max_rounds: int = 5,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[dict]:
    messages = [{"role": "user", "content": prompt}]

    for round_num in range(max_rounds):
        content_buffer = ""
        tool_call_buffers: dict[int, dict] = {}

        async for event in provider.stream_generate_with_tools(prompt if round_num == 0 else "", tools, temperature, max_tokens):
            if event["type"] == "content":
                content_buffer += event["data"]
                yield {"type": "content", "data": event["data"]}
            elif event["type"] == "tool_call":
                tool_call_buffers[len(tool_call_buffers)] = event["data"]
                yield {"type": "tool_call_start", "data": {"name": event["data"]["name"]}}
            elif event["type"] == "done":
                pass

        if not tool_call_buffers:
            yield {"type": "done", "data": {"finish_reason": "stop", "round": round_num}}
            return

        tool_calls_list = [tool_call_buffers[i] for i in sorted(tool_call_buffers.keys())]

        if hasattr(provider, "generate_with_messages"):
            messages = _append_assistant_message(messages, GenerateResult(
                content=content_buffer,
                model="",
                provider=provider.provider if hasattr(provider, 'provider') else "unknown",
                tool_calls=tool_calls_list,
            ), provider)
        else:
            messages.append({
                "role": "assistant",
                "content": content_buffer or None,
                "tool_calls": [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                } for tc in tool_calls_list],
            })

        for tc in tool_calls_list:
            tool_name = tc["name"]
            try:
                arguments = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
            except json.JSONDecodeError:
                arguments = {}
            yield {"type": "tool_execution", "data": {"name": tool_name}}
            tool_result = await tool_executor.execute(tool_name, arguments)
            yield {"type": "tool_result", "data": {"name": tool_name, "result": tool_result[:500]}}

            if provider.provider == "anthropic":
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tc["id"], "content": tool_result}],
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })

    yield {"type": "done", "data": {"finish_reason": "max_rounds_reached"}}


async def _call_llm_with_messages(
    provider: LLMProvider,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
) -> GenerateResult:
    if hasattr(provider, "generate_with_messages"):
        return await provider.generate_with_messages(messages, tools, temperature, max_tokens)

    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                last_user_msg = content
            break

    return await provider.generate_with_tools(last_user_msg, tools, temperature, max_tokens)


def _append_assistant_message(messages: list[dict], result: GenerateResult, provider: LLMProvider) -> list[dict]:
    if provider.provider == "anthropic":
        content_blocks = []
        if result.content:
            content_blocks.append({"type": "text", "text": result.content})
        for tc in result.tool_calls:
            try:
                inp = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
            except json.JSONDecodeError:
                inp = {}
            content_blocks.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": inp,
            })
        messages.append({"role": "assistant", "content": content_blocks})
    else:
        msg = {
            "role": "assistant",
            "content": result.content or None,
            "tool_calls": [{
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            } for tc in result.tool_calls],
        }
        messages.append(msg)
    return messages
