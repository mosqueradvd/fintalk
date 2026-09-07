# FinTalk

Full-stack app that serves **quarterly KPI estimates** (historical + quarter-to-date)
for public companies to time-poor investors — through a **natural-language chat**
and through an **MCP server** that external AI clients (Claude Desktop, Cursor)
can consume.

Take-home for the AI Infrastructure Senior Engineer role at YipitData.
Assignment statement: [`docs/take-home-assignment.md`](docs/take-home-assignment.md).

---

## Architecture

```mermaid
flowchart TD
    UI["Frontend (React/Vite)<br/>chat + tool-call panel"]
    EXT["External AI client<br/>(Claude Desktop, Cursor)"]

    subgraph Backend["Python backend"]
        API["REST API (FastAPI)<br/>/companies, /sectors, /chat"]
        ORCH["Chat orchestrator<br/>Claude (Haiku) tool-use loop"]
        MCP["MCP server (FastMCP)<br/>find_company · list_company_kpis<br/>get_history · get_qtd · list_all_sectors"]
        CORE["core/ — shared service layer<br/>pure, typed functions · all SQL"]
    end

    DB[("Postgres<br/>companies · kpis<br/>quarterly_estimates · qtd_estimates")]
    ANTHROPIC["Claude API"]

    UI -->|"POST /chat"| API
    API --> ORCH
    ORCH <-->|"MCP over stdio<br/>(real client)"| MCP
    ORCH <-->|tool-use| ANTHROPIC
    EXT <-->|"MCP over stdio"| MCP
    API --> CORE
    MCP --> CORE
    CORE --> DB
```

**The one idea that shapes everything:** a shared `core/` layer of pure, typed
functions. The REST API and the MCP tools both import it — no duplicated
queries, and no `MCP → REST → DB` double hop. See
[core/README.md](core/README.md).

**The chat backend is a real MCP client.** It doesn't call `core/` directly; it
spawns our MCP server over stdio and drives a Claude tool-use loop against it.
So the exact tool path our frontend exercises is the one external clients use —
we dogfood it. See [chat/README.md](chat/README.md).

Request lifecycle and a sequence diagram: [docs/architecture.md](docs/architecture.md).

---

## Running it

### Prerequisites
- Python 3.11+ (developed on 3.14), Node 18+
- Docker (for Postgres), or a local Postgres
- A Claude API key ([console.anthropic.com](https://console.anthropic.com)) — only for `/chat`

### 1. Database

```bash
docker compose -f db/docker-compose.yml up -d

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://fintalk:fintalk@localhost:5432/fintalk
psql "$DATABASE_URL" -f db/schema.sql
python db/load_csv.py kpi_sample_2000__282_29__281_29.csv
```

### 2. Config

```bash
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY
```

### 3. Backend (REST + chat)

```bash
uvicorn api.main:app --reload --port 8000      # docs at /docs
```

### 4. Frontend

```bash
cd frontend && npm install && npm run dev      # http://localhost:5173
```

### 5. MCP server (standalone, for external clients)

```bash
python -m mcp_server.server                     # stdio transport
```

### Tests & evals

```bash
pip install -r requirements-dev.txt
make test          # 16 unit tests; skip automatically if Postgres is down
make eval          # behavioural evals — real model + tools (needs ANTHROPIC_API_KEY, ~$0.05)
```

Two layers, on purpose:

- **`make test`** — plumbing. Scripted mock LLM (no API cost, deterministic),
  but the **real** MCP server subprocess and sample DB.
- **`make eval`** — behaviour. The real orchestrator + real model
  (`temperature=0`) against the sample DB: does a plain-English question hit
  the right tools and report the right number? Prints pass-rate, tool
  precision, and cost/latency per case; non-zero exit can gate a deploy.
  See [evals/README.md](evals/README.md).

---

## Connecting an external MCP client

`claude_desktop_config.json` (`~/Library/Application Support/Claude/`):

```json
{
  "mcpServers": {
    "fintalk": {
      "command": "/ABSOLUTE/PATH/fintalk/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/ABSOLUTE/PATH/fintalk",
      "env": { "DATABASE_URL": "postgresql://fintalk:fintalk@localhost:5432/fintalk" }
    }
  }
}
```

Restart Claude Desktop → the 5 tools appear. Full details, including Cursor:
[mcp_server/README.md](mcp_server/README.md).

---

## Key design decisions

| Decision | Why |
|----------|-----|
| **Shared `core/` service layer** | Single source of truth for SQL + business logic; REST and MCP are thin adapters over it. No double hop. |
| **Chat backend = real MCP client (stdio)** | One tool path, tested once, used by both our UI and external clients. |
| **`estimate_type` splits into two tables** (`quarterly_estimates`, `qtd_estimates`) | Different natural keys — one value per (kpi, quarter) vs. many snapshots per (kpi, as_of_date). Merging them would force a conditional unique constraint and half-empty columns. See [db/schema.sql](db/schema.sql). |
| **No free SQL from the LLM** | The LLM calls typed functions; every query in `core/db.py` is parameterized. Invalid input → structured error, never an injection path. This is the LLM↔data security boundary. |
| **Recoverable tool errors** | A miss returns `{"error": "kpi_not_found", "message": ..., "suggestions": [...]}`, not an exception. The model retries with a suggestion — observed working in the logs. |
| **`core/` returns dataclasses, not pydantic** | Keeps `core/` framework-agnostic; adapters serialize. |
| **Haiku by default** | Cheapest model that handles the loop; overridable via `CHAT_MODEL`. |
| **Vite SPA, not Next.js** | The frontend is deliberately thin (compose → `POST /chat` → render). SSR buys nothing here; less toolchain to explain and maintain. |
| **`FastMCP` from the MCP SDK**, not the standalone `fastmcp` package | `fastmcp` v4 pulls `starlette` 1.x and breaks FastAPI 0.115. The SDK's `mcp.server.fastmcp` is the original FastMCP and is enough. `starlette` is pinned. |

---

## Observability & auditing

Structured JSON logs, one line per event, correlated by `request_id` across the
whole `/chat` tool-use loop. Two surfaces:

- `logs/app.log` — everything (HTTP access, chat lifecycle, errors + tracebacks)
- `logs/mcp_audit.log` — append-only tool-call audit (works for any MCP client)

Every `chat_completed` line carries **token spend** for the turn —
`llm_calls`, `input_tokens`, `output_tokens`, `cost_usd`
(`chat/pricing.py`; also on `ChatResult.usage`). Internal signal for cost
dashboards and the eval harness, not shown to end users.

Details, an example trace showing LLM error-recovery, and the error-handling
policy per layer: [docs/observability.md](docs/observability.md).

---

## Security review

[SECURITY.md](SECURITY.md) — OWASP Top 10 for LLM Applications (2025) plus a
light STRIDE pass over the LLM↔MCP↔Core↔DB boundary, each finding anchored to
code. Small mitigations were applied inline (LIKE-wildcard scoping on lookups,
single-quarter scoping for QTD, `quarters` clamped in `core/`, a `question`
length cap); larger items (auth, read-only DB role, rate limiting, moving
QoQ/YoY math into `core/`) are listed there as production work.
[docs/audit-report.md](docs/audit-report.md) covers the matching
performance / integrity / MCP-conformance review.

---

## Future improvements

- **`compare_qtd_vs_prior_quarter` tool.** "QTD vs last quarter" currently needs
  the model to combine `get_qtd` + `get_history`; a weak model sometimes compares
  two QTD snapshots instead. A dedicated tool would make it robust.
- **Persistent MCP session.** `/chat` spawns the MCP server per request (~1s
  startup). Pool a long-lived session in the API lifespan.
- **Streaming responses** to the UI (SSE) — answers currently arrive whole.
- **Trace propagation into `mcp_audit.log`.** Carry W3C trace context through
  MCP request metadata; emit OpenTelemetry spans; ship logs to an aggregator.
  `latency_ms` fields are already metric-ready.
- **Multi-tenant data isolation.** Row-level scoping in `core/` + a tenant claim
  on the request; the `core/` boundary is the natural enforcement point.
- **Production auth for the Claude API** via workload identity federation
  (no static key) once this runs in a cloud container.
- **Conversation memory** — the orchestrator is currently single-turn.
- **KPI value typing** — units are strings (`$MM`, `subs`); a units/enums table
  would enable safe cross-KPI math.

---

## Where AI was used vs. manual decisions

AI (Claude Code) was used heavily and is not penalized by the assignment — what
matters is knowing when to trust it and when a problem needed deliberate design.

**Deliberate, human-owned decisions:**
- The data model, especially the `historical` / `qtd` table split and the
  choice of natural keys.
- The MCP **tool schema** — names, parameters, and granularity — designed from
  "how would an agent naturally explore this?" (discover → list KPIs → pull
  data), then narrowed to 5 tools.
- The **error contract** (`{error, message, suggestions}`) and the decision that
  tool misses return payloads, not exceptions.
- The **LLM↔data security boundary**: no generated SQL, typed functions only,
  parameterized queries in one place.
- The **shared `core/` layer** and "chat is a real MCP client" architecture.
- Dependency conflict resolution (FastMCP vs. FastAPI/starlette).
- Choosing Vite over Next.js for scope.

**AI-generated, then reviewed:** most implementation code, the CSV loader,
boilerplate (FastAPI wiring, React components, dataclasses), test scaffolding,
and first drafts of this documentation.

**Bugs AI introduced and we caught by testing the real flow:**
- `extract_tool_payload` read only the first content block, so list-returning
  tools fed the LLM 1 of N results — the model's wrong answer was faithful to
  broken input, not a hallucination.
- `find_company` didn't match on sector, so "companies in the Fintech sector"
  failed until a sample question surfaced it in the UI.

---

## Repo layout

```
core/         shared service layer — pure functions, all SQL, typed errors
api/          FastAPI REST adapter + /chat endpoint
mcp_server/   FastMCP server (5 tools) + tool-call audit
chat/         chat orchestrator — real MCP client + Claude tool-use loop
frontend/     Vite + React SPA (chat + tool-call panel)
db/           schema.sql, CSV loader, docker-compose
docs/         assignment, architecture, observability, audit-report
tests/        pytest (mock LLM, real MCP + DB)
evals/        behavioural evals (real model + tools)
```

Branching follows git-flow: `main` ← `develop` ← `feature/*`.
