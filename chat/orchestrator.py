"""The tool-use loop: question in, grounded answer + tool-call trace out."""

from __future__ import annotations

import json
import time

from .config import MAX_TOOL_ITERATIONS, SYSTEM_PROMPT
from .llm import AnthropicLLM, LLMClient
from .mcp_client import extract_tool_payload, mcp_session, to_anthropic_tools
from .schemas import ChatResult, ToolCall


async def run_chat(question: str, llm: LLMClient | None = None) -> ChatResult:
    llm = llm or AnthropicLLM()
    tool_calls: list[ToolCall] = []

    async with mcp_session() as session:
        tools = to_anthropic_tools((await session.list_tools()).tools)
        messages: list[dict] = [{"role": "user", "content": question}]

        for _ in range(MAX_TOOL_ITERATIONS):
            resp = llm.create(
                system=SYSTEM_PROMPT, messages=messages, tools=tools
            )
            messages.append({"role": "assistant", "content": resp.assistant_content})

            if resp.stop_reason != "tool_use":
                return ChatResult(
                    answer=resp.text, model=llm.model, tool_calls=tool_calls
                )

            results_block = []
            for tu in resp.tool_uses:
                started = time.perf_counter()
                raw = await session.call_tool(tu.name, tu.args)
                latency_ms = round((time.perf_counter() - started) * 1000, 1)

                payload = extract_tool_payload(raw)
                ok = not (isinstance(payload, dict) and "error" in payload)
                tool_calls.append(
                    ToolCall(tu.name, tu.args, payload, latency_ms, ok)
                )
                results_block.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(payload, default=str),
                        "is_error": not ok,
                    }
                )
            messages.append({"role": "user", "content": results_block})

    return ChatResult(
        answer="I couldn't finish answering within the tool-call limit. "
        "Try a more specific question.",
        model=llm.model,
        tool_calls=tool_calls,
    )
