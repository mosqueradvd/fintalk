# chat/ — chat orchestrator

Turns a natural-language question into a grounded answer + a tool-call trace.

```
question ─▶ run_chat ─┬─▶ MCP session (spawns `python -m mcp_server.server`)
                      └─▶ LLM (Haiku) tool-use loop
                                │
        ┌───────────────────────┴───────────────────────┐
        │  LLM asks for a tool → we call it via MCP →    │
        │  feed the result back → repeat until it answers │
        └───────────────────────────────────────────────┘
                      ▼
          ChatResult{ answer, model, tool_calls[] }
```

## Why go through MCP (not call `core/` directly)

The frontend exercises the **exact** tool path an external client (Claude
Desktop, Cursor) uses. One code path to test, one to harden.

## Files

| File | Role |
|------|------|
| `llm.py` | `LLMClient` protocol · `AnthropicLLM` (real) · `MockLLM` (scripted, no API cost) |
| `mcp_client.py` | spawn + connect to our MCP server; MCP↔Anthropic tool-schema glue |
| `orchestrator.py` | the tool-use loop, capped at `MAX_TOOL_ITERATIONS` |
| `schemas.py` | `ChatResult`, `ToolCall` |
| `config.py` | model, prompt, limits; loads `.env` |

## Cost control

- All logic + tests run on `MockLLM` — deterministic, zero API calls.
- Default model is **Haiku**; override with `CHAT_MODEL`.
- `AnthropicLLM` is only constructed when `run_chat` is called without a
  `llm=` override.

## Known limitation

The loop grounds every number in a tool result, but "QTD vs *last quarter*"
needs the model to combine `get_qtd` + `get_history`; a weak model may compare
two QTD snapshots instead. Prompt nudges this; a dedicated
`compare_qtd_vs_prior_quarter` tool would make it robust (see root README →
future improvements).
