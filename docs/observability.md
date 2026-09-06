# Observability & error handling

## What is logged

One JSON line per event (`core/obs.py`), to **stderr** and **`logs/app.log`**.
Tool calls are additionally written to an append-only **`logs/mcp_audit.log`**.

| Event | Emitted by | Key fields |
|-------|-----------|-----------|
| `http_request` | API middleware | method, path, status, latency_ms |
| `service_error` | API | code, message |
| `unhandled_exception` / `http_unhandled` | API | path, error (+ traceback) |
| `chat_started` | orchestrator | question, model |
| `tool_call` | orchestrator **and** MCP server | tool, args, ok/outcome, latency_ms |
| `chat_completed` | orchestrator | model, tools (count), latency_ms |
| `chat_failed` | orchestrator | error (+ traceback) |

## Correlation: `request_id`

The API middleware assigns a `request_id` (or honours an inbound
`X-Request-ID`) and echoes it on the response. It is carried in a `contextvar`,
so every line from the same HTTP request — including the whole chat tool-use
loop — shares it. Example (one `/chat` call, trimmed):

```
chat_started      request_id=ddd0acbdb50e  question="Total Revenue history for CloudNine..."
tool_call         request_id=ddd0acbdb50e  tool=find_company            ok=true
tool_call         request_id=ddd0acbdb50e  tool=get_history kpi="Total Revenue"      ok=false   ← LLM used wrong name
tool_call         request_id=ddd0acbdb50e  tool=get_history kpi="Total Revenue ($MM)" ok=true    ← recovered from suggestions
chat_completed    request_id=ddd0acbdb50e  tools=3  latency_ms=6332
http_request      request_id=ddd0acbdb50e  POST /chat  status=200
```

That trace is also the evidence of **LLM error recovery**: a `kpi_not_found`
with `suggestions` let the model retry successfully instead of failing.

## Error handling policy

| Layer | On failure |
|-------|-----------|
| `core/` | raises `ServiceError` (never a bare exception for expected misses) |
| REST API | `ServiceError` → its `http_status` + `{error, message, suggestions}`; anything else → `500 {"error":"internal_error"}` + logged traceback |
| MCP tools | lookup misses returned as `{error, ...}` payloads, not exceptions |
| Chat orchestrator | catch-all boundary: always returns a `ChatResult` (graceful answer + any completed tool calls), never propagates a 500 |
| Frontend | error shown in a dedicated red bubble |

## Known gaps / production extension

- **`mcp_audit.log` lines show `request_id="-"`.** The MCP server is a separate
  process; the contextvar doesn't cross the boundary. Our own path is still
  fully correlated (the orchestrator logs every `tool_call` with the id).
  In production: propagate W3C trace context through MCP request metadata and
  emit OpenTelemetry spans.
- Logs are local files. Production: ship to a log aggregator; the JSON lines
  are already structured for it. `chat_completed.latency_ms` and per-`tool_call`
  latency are ready to become metrics/histograms.
- No sampling or PII scrubbing on `question` / `args` yet.
