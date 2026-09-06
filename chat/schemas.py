"""Return shapes for the chat orchestrator (serialized to the frontend)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
