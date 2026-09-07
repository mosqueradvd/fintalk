# Behavioural evals

`pytest` (in `tests/`) proves the **plumbing**: the `core/` queries, the MCP
tool loop, error translation. It uses a scripted mock LLM, so it never checks
the one thing a user actually cares about:

> Given a plain-English question, does the agent call the right tools and
> report the right number?

That's what this harness measures. It runs the **real** orchestrator against
the **real** model (`temperature=0` for determinism) and the sample DB.

## Run

```bash
python -m evals                       # all cases, must be 100% to exit 0
python -m evals --min-pass 0.8        # allow a 20% miss rate
python -m evals --only qtd_latest_value
python -m evals --json evals/last_run.json
```

Needs `ANTHROPIC_API_KEY` and the loaded sample DB. Without either it prints a
notice and exits 0 (so it's safe to drop into a pipeline that doesn't always
have secrets). One run is ~6 Haiku conversations, about **$0.05** and ~40s —
the cost is printed per case and in total.

## What a case looks like

`cases.json`, one object per case:

| field | meaning |
|---|---|
| `question` | what the user types |
| `expect_tools` | tool names that **must** all appear in the trace |
| `expect_value` | `{kind, ticker, kpi}` — the harness resolves the true number from `core/` **at run time** (so cases don't rot when data is reloaded) and checks the answer states it |
| `expect_contains_any` | answer must contain at least one of these strings |
| `forbid_value` | e.g. `any_number_over` — guards against a fabricated figure |
| `no_tool_errors` | every tool call in the trace returned `ok` |

Every case also gets an implicit `answered` check (non-empty response).

## Metrics

- **pass_rate** — fraction of cases where every check passed. This is the
  headline and the CI gate.
- **tool_precision** — of the cases that declared `expect_tools`, the fraction
  whose expected tools were all called. Catches "the model answered from the
  wrong tool / skipped a step".
- **cost / latency** — per case and total, from `ChatResult.usage`
  (`chat/pricing.py`).

## As a deploy gate

`python -m evals --min-pass 0.9` in CI, after unit tests, before a deploy step.
Non-zero exit blocks the pipeline. Pair it with a golden-value check per KPI
once QoQ/YoY math moves into `core/` (see `SECURITY.md` LLM09 and
`docs/audit-report.md` §3.2).

## Notes from building this

The harness immediately caught that the agent **skips `find_company` when the
question already contains a ticker** ("IGC") — reasonable behaviour, but it
means `expect_tools` has to describe what's *necessary*, not what the system
prompt suggests. That's the kind of gap a plumbing test never shows.
