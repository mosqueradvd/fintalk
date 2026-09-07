"""Return shapes for the chat orchestrator (serialized to the frontend)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .pricing import Usage


@dataclass
class ToolCall:
    """One MCP tool invocation, surfaced to the UI's tool-call panel."""

    name: str
    args: dict
    result: Any
    latency_ms: float
    ok: bool


@dataclass
class ChatResult:
    answer: str
    model: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Token spend for this turn. Internal observability (logs, eval harness,
    # cost dashboards) — the UI doesn't need to surface it.
    usage: Usage = field(default_factory=Usage)
