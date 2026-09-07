"""Token/cost aggregation — pure, no DB, no API."""

from chat.pricing import Usage


def test_haiku_rates():
    u = Usage()
    u.add("claude-haiku-4-5-20251001", input_tokens=1_000_000, output_tokens=0)
    u.add("claude-haiku-4-5-20251001", input_tokens=0, output_tokens=1_000_000)
    assert u.llm_calls == 2
    assert u.input_tokens == 1_000_000
    assert u.output_tokens == 1_000_000
    assert round(u.cost_usd, 4) == 6.0  # $1/1M in + $5/1M out


def test_unknown_model_falls_back_to_haiku_class():
    u = Usage()
    u.add("some-future-model", input_tokens=1_000_000, output_tokens=0)
    assert round(u.cost_usd, 4) == 1.0
