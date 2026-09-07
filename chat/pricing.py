"""Token pricing for the chat models we might run.

Kept as a tiny local table on purpose: cost/latency observability shouldn't
depend on a network call, and the numbers move rarely. Prices are USD per 1M
tokens, first-party Anthropic API rates (console.anthropic.com/pricing).

This is an *internal* signal — it feeds the structured logs and the eval
harness so we can answer "what does a chat turn cost?", not something shown
to end users.
"""

from __future__ import annotations

from dataclasses import dataclass

# (input $/1M, output $/1M). Match on a prefix so a dated model id
# ("claude-haiku-4-5-20251001") still resolves.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5": (5.00, 25.00),
}

_FALLBACK = (1.00, 5.00)  # assume Haiku-class if we don't recognise the id


@dataclass
class Usage:
    """Aggregated token spend for one chat turn (all LLM calls combined)."""

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, model: str, input_tokens: int, output_tokens: int) -> None:
        in_rate, out_rate = _rate_for(model)
        self.llm_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += (
            input_tokens * in_rate + output_tokens * out_rate
        ) / 1_000_000


def _rate_for(model: str) -> tuple[float, float]:
    for prefix, rate in _PRICES.items():
        if model.startswith(prefix):
            return rate
    return _FALLBACK
