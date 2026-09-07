"""Load cases, run them through the real agent, score the results."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chat.orchestrator import run_chat
from chat.schemas import ChatResult
from core.service import get_kpi_history, get_qtd_estimate

_CASES_FILE = Path(__file__).parent / "cases.json"

# money in answers is formatted "627.45" / "1,203.90" — two decimals
_MONEY_RE = re.compile(r"\d[\d,]*\.\d{2}")


def load_cases(path: Path | None = None) -> list[dict]:
    return json.loads((path or _CASES_FILE).read_text())


# --------------------------------------------------------------------------- #
# Ground truth — resolved from core/ at run time so cases don't rot when the
# sample data is reloaded.
# --------------------------------------------------------------------------- #


def expected_number(spec: dict) -> float:
    kind = spec["kind"]
    if kind == "qtd_latest":
        return get_qtd_estimate(spec["ticker"], spec["kpi"]).latest.value
    if kind == "history_latest":
        return get_kpi_history(spec["ticker"], spec["kpi"]).points[-1].value
    raise ValueError(f"unknown expect_value kind: {kind!r}")


def _answer_has_number(answer: str, value: float) -> bool:
    """True if the answer states `value` at 0-2 decimals (comma-insensitive)."""
    flat = answer.replace(",", "")
    return any(
        f"{value:.{d}f}" in flat for d in (2, 1, 0)
    )


def _money_numbers(answer: str) -> list[float]:
    return [float(m.replace(",", "")) for m in _MONEY_RE.findall(answer)]


# --------------------------------------------------------------------------- #
# Run + score
# --------------------------------------------------------------------------- #


@dataclass
class CaseResult:
    name: str
    passed: bool
    checks: dict[str, bool]
    answer: str
    tools_called: list[str]
    latency_s: float
    cost_usd: float
    error: str | None = None


@dataclass
class SuiteResult:
    cases: list[CaseResult] = field(default_factory=list)
    wall_s: float = 0.0

    @property
    def pass_rate(self) -> float:
        return sum(c.passed for c in self.cases) / len(self.cases) if self.cases else 0.0

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd for c in self.cases)

    @property
    def tool_precision(self) -> float:
        """Over cases that declared expect_tools: fraction whose expected tools
        were all called."""
        scored = [c for c in self.cases if "tools" in c.checks]
        return sum(c.checks["tools"] for c in scored) / len(scored) if scored else 1.0


def score(case: dict, res: ChatResult) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    answer = res.answer or ""
    tools = [tc.name for tc in res.tool_calls]

    if "expect_tools" in case:
        checks["tools"] = all(t in tools for t in case["expect_tools"])

    if case.get("no_tool_errors"):
        checks["no_tool_errors"] = all(tc.ok for tc in res.tool_calls)

    if "expect_value" in case:
        want = expected_number(case["expect_value"])
        checks["value"] = _answer_has_number(answer, want)

    if "expect_contains_any" in case:
        low = answer.lower()
        checks["contains_any"] = any(
            s.lower() in low for s in case["expect_contains_any"]
        )

    if "forbid_value" in case:
        spec = case["forbid_value"]
        if spec["kind"] == "any_number_over":
            checks["no_fabricated_number"] = not any(
                n > spec["value"] for n in _money_numbers(answer)
            )

    # A non-empty answer is table stakes for every case.
    checks["answered"] = bool(answer.strip())
    return checks


async def run_case(case: dict) -> CaseResult:
    t0 = time.perf_counter()
    try:
        res = await run_chat(case["question"])
    except Exception as exc:  # noqa: BLE001 — harness must not crash on one case
        return CaseResult(
            name=case["name"],
            passed=False,
            checks={},
            answer="",
            tools_called=[],
            latency_s=round(time.perf_counter() - t0, 2),
            cost_usd=0.0,
            error=f"{type(exc).__name__}: {exc}",
        )

    checks = score(case, res)
    return CaseResult(
        name=case["name"],
        passed=all(checks.values()),
        checks=checks,
        answer=res.answer,
        tools_called=[tc.name for tc in res.tool_calls],
        latency_s=round(time.perf_counter() - t0, 2),
        cost_usd=res.usage.cost_usd,
    )


async def run_suite(cases: list[dict]) -> SuiteResult:
    t0 = time.perf_counter()
    suite = SuiteResult()
    for case in cases:
        suite.cases.append(await run_case(case))
    suite.wall_s = round(time.perf_counter() - t0, 1)
    return suite


def to_dict(suite: SuiteResult) -> dict[str, Any]:
    return {
        "pass_rate": round(suite.pass_rate, 3),
        "tool_precision": round(suite.tool_precision, 3),
        "total_cost_usd": round(suite.total_cost, 6),
        "wall_s": suite.wall_s,
        "cases": [
            {
                "name": c.name,
                "passed": c.passed,
                "checks": c.checks,
                "tools_called": c.tools_called,
                "latency_s": c.latency_s,
                "cost_usd": round(c.cost_usd, 6),
                "answer": c.answer,
                "error": c.error,
            }
            for c in suite.cases
        ],
    }
