"""The tool-use loop: question in, grounded answer + tool-call trace out.

Failure policy: the frontend always gets a ChatResult, never a 500. Anything
that goes wrong (no API key, Anthropic error, MCP server won't start, a bug)
is logged with the request id and returned as a graceful answer plus whatever
tool calls completed before the failure.
"""

from __future__ import annotations

import json
import time

from core.obs import get_logger, log_event, request_context

from .config import CHAT_MODEL, MAX_TOOL_ITERATIONS, SYSTEM_PROMPT
from .llm import AnthropicLLM, LLMClient
from .mcp_client import extract_tool_payload, mcp_session, to_anthropic_tools
from .pricing import Usage
from .schemas import ChatResult, ToolCall

_log = get_logger("chat")

_FALLBACK = (
    "Sorry — I hit an internal error answering that. It's been logged; "
    "please try again."
)


def _unwrap(exc: BaseException) -> BaseException:
    """anyio wraps failures from the MCP session in an ExceptionGroup; peel a
    single-cause group so the log names the real error."""
    while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc


async def run_chat(question: str, llm: LLMClient | None = None) -> ChatResult:
    with request_context():
        tool_calls: list[ToolCall] = []
        usage = Usage()
        model = getattr(llm, "model", CHAT_MODEL)
        started = time.perf_counter()
        log_event(_log, "chat_started", question=question, model=model)
        try:
            result = await _run(question, llm, tool_calls, usage)
            log_event(
                _log,
                "chat_completed",
                model=result.model,
                tools=len(result.tool_calls),
                llm_calls=usage.llm_calls,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=round(usage.cost_usd, 6),
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            return result
        except Exception as exc:  # noqa: BLE001 — deliberate catch-all boundary
            root = _unwrap(exc)
            log_event(
                _log,
                "chat_failed",
                error=f"{type(root).__name__}: {root}",
                cost_usd=round(usage.cost_usd, 6),
            )
            _log.exception("chat_failed")
            return ChatResult(
                answer=_FALLBACK, model=model, tool_calls=tool_calls, usage=usage
            )


async def _run(
    question: str,
    llm: LLMClient | None,
    tool_calls: list[ToolCall],
    usage: Usage,
) -> ChatResult:
    llm = llm or AnthropicLLM()

    async with mcp_session() as session:
        tools = to_anthropic_tools((await session.list_tools()).tools)
        messages: list[dict] = [{"role": "user", "content": question}]

        for _ in range(MAX_TOOL_ITERATIONS):
            resp = llm.create(system=SYSTEM_PROMPT, messages=messages, tools=tools)
            if resp.usage is not None:
                usage.add(
                    llm.model, resp.usage.input_tokens, resp.usage.output_tokens
                )
            messages.append({"role": "assistant", "content": resp.assistant_content})

            if resp.stop_reason != "tool_use":
                return ChatResult(
                    answer=resp.text,
                    model=llm.model,
                    tool_calls=tool_calls,
                    usage=usage,
                )

            results_block = []
            for tu in resp.tool_uses:
                t0 = time.perf_counter()
                raw = await session.call_tool(tu.name, tu.args)
                latency_ms = round((time.perf_counter() - t0) * 1000, 1)

                payload = extract_tool_payload(raw)
                ok = not (isinstance(payload, dict) and "error" in payload)
                tool_calls.append(ToolCall(tu.name, tu.args, payload, latency_ms, ok))
                log_event(
                    _log,
                    "tool_call",
                    tool=tu.name,
                    args=tu.args,
                    ok=ok,
                    latency_ms=latency_ms,
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
        usage=usage,
    )
