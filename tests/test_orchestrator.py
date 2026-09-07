"""Chat orchestrator — real MCP server (subprocess), scripted LLM (no API cost)."""

import pytest

from chat.llm import MockLLM
from chat.mcp_client import extract_tool_payload
from chat.orchestrator import run_chat
from core.db import query

try:
    query("SELECT 1")
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = [
    pytest.mark.skipif(not DB_UP, reason="Postgres not reachable"),
    pytest.mark.anyio,
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_happy_path_runs_tools_then_answers():
    script = [
        {"tool": "find_company", "args": {"query": "imaginary"}, "id": "a"},
        {"tool": "get_qtd", "args": {"ticker": "IGC", "kpi": "Total Revenue ($MM)"}, "id": "b"},
        {"text": "IGC QTD revenue is $627.45MM."},
    ]
    res = await run_chat("IGC revenue?", llm=MockLLM(script))

    assert res.answer == "IGC QTD revenue is $627.45MM."
    assert [tc.name for tc in res.tool_calls] == ["find_company", "get_qtd"]
    assert all(tc.ok for tc in res.tool_calls)
    # list-returning tool: full result reaches the trace, not just item 0
    assert res.tool_calls[0].result[0]["ticker"] == "IGC"
    # usage is tracked per turn (MockLLM reports zero tokens -> zero cost)
    assert res.usage.llm_calls == 3
    assert res.usage.cost_usd == 0.0


async def test_tool_error_is_flagged_not_raised():
    script = [
        {"tool": "get_history", "args": {"ticker": "IGC", "kpi": "Revenu"}, "id": "a"},
        {"text": "That KPI doesn't exist; did you mean Total Revenue ($MM)?"},
    ]
    res = await run_chat("history for Revenu?", llm=MockLLM(script))

    assert res.tool_calls[0].ok is False
    assert res.tool_calls[0].result["error"] == "kpi_not_found"


async def test_iteration_limit_is_enforced():
    # LLM that never stops calling tools
    script = [{"tool": "find_company", "args": {"query": "x"}, "id": "a"}] * 20
    res = await run_chat("loop forever", llm=MockLLM(script))
    assert "tool-call limit" in res.answer


async def test_llm_failure_returns_graceful_result_not_exception():
    class BoomLLM:
        model = "boom"

        def create(self, **_):
            raise RuntimeError("simulated Anthropic outage")

    res = await run_chat("anything", llm=BoomLLM())
    assert "internal error" in res.answer.lower()
    assert res.model == "boom"


def test_extract_tool_payload_unwraps_structured_list():
    class R:
        structuredContent = {"result": [{"a": 1}, {"a": 2}]}
        content = []

    assert extract_tool_payload(R()) == [{"a": 1}, {"a": 2}]
