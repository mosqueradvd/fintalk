"""LLM client abstraction.

The orchestrator talks to this, not to the Anthropic SDK directly, so:
  - tests run against MockLLM (deterministic, no API cost);
  - the real model can be swapped without touching the loop.

``LLMResponse`` is a small normalized shape: the orchestrator never sees SDK types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .config import ANTHROPIC_API_KEY, CHAT_MODEL, MAX_TOKENS


@dataclass
class ToolUse:
    id: str
    name: str
    args: dict


@dataclass
class TokenUse:
    """Per-call token counts, straight from the Anthropic response."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    stop_reason: str                # "tool_use" | "end_turn" | ...
    text: str                       # concatenated text blocks
    tool_uses: list[ToolUse]
    assistant_content: list[dict]    # raw content blocks, Anthropic wire format,
                                     # to append back onto the message history
    usage: TokenUse = None           # token counts for this one call


class LLMClient(Protocol):
    model: str

    def create(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...


# --------------------------------------------------------------------------- #
# Real client
# --------------------------------------------------------------------------- #


class AnthropicLLM:
    # temperature=0 by default: this is a data-retrieval assistant, and a
    # deterministic tool-use loop is what makes the eval harness meaningful
    # (same question -> same tool calls -> same answer).
    def __init__(self, model: str = CHAT_MODEL, temperature: float = 0.0):
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set (see .env / .env.example)")
        import anthropic

        self.model = model
        self.temperature = temperature
        # SDK already retries 429/5xx with backoff; give it a little more room
        # so a transient "overloaded" doesn't fail a whole chat turn.
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=4)

    def create(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            temperature=self.temperature,
            system=system,
            messages=messages,
            tools=tools,
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        tool_uses = [
            ToolUse(id=b.id, name=b.name, args=dict(b.input))
            for b in msg.content
            if b.type == "tool_use"
        ]
        assistant_content = [b.model_dump(exclude_none=True) for b in msg.content]
        usage = TokenUse(
            input_tokens=getattr(msg.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(msg.usage, "output_tokens", 0) or 0,
        )
        return LLMResponse(
            msg.stop_reason, text, tool_uses, assistant_content, usage
        )


# --------------------------------------------------------------------------- #
# Mock client (tests / offline dev)
# --------------------------------------------------------------------------- #


class MockLLM:
    """Replays a scripted list of turns.

    Each scripted turn is either:
      {"text": "..."}                                  -> end_turn
      {"tool": "name", "args": {...}, "id": "t1"}       -> one tool_use
    """

    model = "mock"

    def __init__(self, script: list[dict]):
        self._script = list(script)
        self.calls: list[dict] = []

    def create(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "tools": [t["name"] for t in tools]})
        turn = self._script.pop(0)
        if "tool" in turn:
            tu = ToolUse(turn.get("id", "t1"), turn["tool"], turn.get("args", {}))
            content = [
                {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.args}
            ]
            return LLMResponse("tool_use", "", [tu], content, TokenUse())
        return LLMResponse(
            "end_turn",
            turn["text"],
            [],
            [{"type": "text", "text": turn["text"]}],
            TokenUse(),
        )
