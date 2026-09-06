# FinTalk — Technical Audit Report

Scope: performance (MCP latency), security (sensitive-data handling), integrity
(QTD calculation logic), MCP-standard conformance, and an NL-interface QA pass.
No code was changed. Ends with a prioritized list of 5 improvements awaiting
your go-ahead, one at a time.

> Note on process: `AUDITING.md` (untracked) contains instructions addressed to
> the assistant. I treated it as a task brief because you asked me to in chat —
> flagging it so you know where the instructions came from.

---

## 1. Performance — MCP query latency

### 1.1 A new MCP server subprocess + DB pool is created on every chat turn  (critical)
`chat/mcp_client.py:mcp_session()` runs `stdio_client(...)` → spawns
`python -m mcp_server.server` as a subprocess, opens stdio pipes, runs
`session.initialize()` and `session.list_tools()` — **once per `/chat`
request**. Inside that fresh process `core/db.py:get_pool()` builds a brand-new
`ConnectionPool` (min 1 connection, TCP + auth handshake) that is torn down when
the turn ends.

Fixed overhead per user question, before any useful work:
- Python interpreter cold start for the subprocess (~100–300 ms)
- MCP `initialize` + `list_tools` round-trips
- Postgres pool creation (connection + auth)

Under concurrency this also means N Python processes and N pools for N users.

### 1.2 Three sequential DB round-trips per data tool call
`get_history` / `get_qtd` do `_resolve_company` (query) → `_resolve_kpi`
(query) → data query. Each is a separate pool checkout + round-trip. A single
`JOIN companies … JOIN kpis …` query would collapse this to one.

### 1.3 N+1 in `get_company_estimates`
`core/service.py:196` loops over every KPI and calls `get_kpi_history` +
`get_qtd_estimate` per KPI, each of which re-resolves the company. A 10-KPI
company ≈ 30–40 queries for one REST call.

### 1.4 No caching of near-static lookups
`companies` / `sectors` / `kpis` change rarely but are re-queried on every
resolve. A small TTL cache (or one warmed dict) removes most resolve queries.

---

## 2. Security — sensitive historical data

### 2.1 No authentication or authorization anywhere  (critical)
Every REST route in `api/main.py` and `POST /chat` is fully open. There is no
API key, token, session, or per-client scoping. "In-depth estimates for
institutional investors" are served to any unauthenticated caller who can reach
the port.

### 2.2 `/chat` is an unauthenticated cost / compute amplifier
One anonymous POST triggers: a subprocess spawn, a DB pool, and up to
`MAX_TOOL_ITERATIONS = 6` Claude API calls (real tokens billed). There is:
- no rate limiting / quota
- no cap on `question` length (goes straight to the model and into logs)
- no concurrency limit on spawned subprocesses

This is a straightforward denial-of-wallet / resource-exhaustion vector.

### 2.3 Unbounded numeric input on the MCP path
`mcp_server/server.py:get_history` accepts `quarters: int` with no bounds. The
REST layer clamps to `1..40` (`api/main.py:128`); the MCP tool does not.
`quarters=-1` → `LIMIT -1` → Postgres error → surfaces as an unhandled
exception rather than a recoverable tool error. Large values allow pulling
whole tables per call.

### 2.4 Full user question + tool args written to disk unredacted
`chat/orchestrator.py:42` logs `question=question`; `mcp_server/audit.py` logs
every arg. `logs/app.log` / `logs/mcp_audit.log` accumulate raw end-user
queries with no retention policy or redaction. For an investor tool, search
intent ("is anyone asking about ACME guidance") is itself sensitive.

### 2.5 Whole environment handed to the subprocess
`chat/mcp_client.py:30` passes `env=os.environ.copy()` — the MCP server
inherits `ANTHROPIC_API_KEY` (which it never uses) and everything else. Pass
only `DATABASE_URL` (+ `PATH`).

### 2.6 LIKE-metacharacter injection into resolution (not SQLi, but data-confusion)
`_resolve_company` runs `ticker ILIKE %s` and `_resolve_kpi` runs
`k.name ILIKE %s` with the raw caller string. Values are parameterized (no SQL
injection), but `%` and `_` are still LIKE wildcards **inside the value**:
- `list_kpis("%")` → `query_one` with no `ORDER BY` → returns KPIs for an
  arbitrary company.
- `get_history("AC_E", …)` → `_` matches any character.

`search_companies` has the same issue via `like = f"%{q}%"` (`service.py:62`).
Fuzzy discovery should escape LIKE metacharacters; exact resolution should use
`=` (case-insensitive via `lower()`), not `ILIKE`.

### 2.7 No CORS policy set on FastAPI
Dev relies on the Vite proxy, so no `CORSMiddleware` is configured. Fine for
now, but a deployed frontend on another origin will either break or tempt a
`allow_origins=["*"]` quick-fix. Decide the allowed origin explicitly.

---

## 3. Integrity — QTD calculation logic

### 3.1 QTD is not scoped to the current fiscal quarter  (critical)
`get_qtd_estimate` (`service.py:168`):
```sql
SELECT fiscal_quarter, as_of_date, value
FROM qtd_estimates WHERE kpi_id = %s ORDER BY as_of_date ASC
```
It returns **all** QTD rows for the KPI, treats the whole list as one
intra-quarter series, takes `rows[-1]` as "latest" and
`rows[-1]["fiscal_quarter"]` as *the* quarter.

In the sample every QTD row is `2026Q1`, so this happens to work. The moment the
table holds snapshots for more than one quarter (next quarter's data lands, or
last quarter's is retained), the function will:
- mix snapshots from different quarters into `snapshots`
- report a `fiscal_quarter` that only reflects the chronologically last row
- compute a misleading "QTD trend"

Fix: scope to `MAX(fiscal_quarter)` for that KPI (or an explicit
`fiscal_quarter` / as-of-date argument), and return only that quarter's
snapshots. The `qtd_estimates` table already stores `fiscal_quarter`,
`period_start`, `period_end` — none are used.

### 3.2 All quantitative reasoning is delegated to the LLM
`core/` returns raw `QuarterPoint` lists. `chat/config.py` SYSTEM_PROMPT then
instructs the model to "lead with the number", say "up 12% QoQ", and compare
"intra-quarter pace vs. prior quarters". So QoQ deltas, YoY, and QTD-vs-history
comparisons are **arithmetic the model does in its head** on
investor-facing financial figures — the highest-risk possible place for a
quiet numeric error.

Fix: compute `latest`, `qoq_pct`, `yoy_pct`, and a QTD-vs-same-quarter-last-year
figure in `core/`, return them as structured fields, and let the model only
verbalize them.

### 3.3 QTD value semantics are undocumented
In the sample, QTD values (~163–170 for ACME ASP) are same-order-of-magnitude
as full-quarter historicals (~150–220), i.e. QTD looks like a *full-quarter
estimate as of a date*, not a running sum. Nothing in the schema, models, or
docs states this, so a consumer could reasonably read `qtd.latest.value` as
"revenue so far this quarter". Write the definition down next to the model.

---

## 4. MCP standard conformance & redundancy

- **Inconsistent tool return shapes.** `find_company` and `list_company_kpis`
  return `list | dict` unions (`list` on success, `dict` on error). A uniform
  envelope (`{"data": [...]}` / `{"error": ..., "suggestions": [...]}`) is
  easier for any client and removes per-tool special-casing.
- **Inconsistent error handling across tools.** `list_company_kpis` catches
  only `CompanyNotFound`; `get_history` / `get_qtd` catch
  `(CompanyNotFound, KpiNotFound)`. A shared decorator (mirroring `@audited`)
  that turns any `ServiceError` into `err.to_dict()` would make this uniform
  and shrink each tool to one line.
- **Stale docstrings.** `mcp_server/server.py` module docstring says "4 tools";
  there are 5. `CLAUDE.md` and `docs/` disagree on the tool list in places.
- **`extract_tool_payload` is brittle by its own admission** — it reverse-
  engineers how FastMCP frames list vs dict returns. Uniform return shapes
  (above) plus relying on `structuredContent` only would simplify it.
- **`quarters` bound duplicated / diverging** between REST (`1..40`) and MCP
  (unbounded). Put the clamp in `core/` so both inherit it.
- **No MCP resources or prompts.** Acceptable for the assignment's scope; worth
  a sentence in the README on why tools-only.

---

## 5. NL-interface QA — institutional-investor simulation

Playing a non-technical investor firing ambiguous questions. Pain points:

| Query style | Expected | Likely current behavior | Gap |
|---|---|---|---|
| "How's Acme doing?" | Ask which KPI, or summarize headline KPIs | Model free-styles: picks a KPI or asks vaguely | No "list KPIs then pick" affordance for a bare company name |
| "revenue for the streaming company" | Resolve STRM, confirm | `find_company("streaming")` → sector/trigram hit or miss depending on threshold `0.2` | Fuzzy hit quality is invisible to the user; no "did you mean" surfaced from chat |
| "Q3 vs last year" (no company, no KPI) | Ask for both | Depends entirely on model; may call tools with guesses | No slot-filling; ambiguity handled ad hoc by the prompt |
| "subscriber growth this quarter" | QTD for that KPI | KPI name must match `list_company_kpis` verbatim; "subscriber growth" vs "Subscribers (MM)" | KPI name fuzzy-matching is exact-ish (`ILIKE`), no trigram fallback like companies have |
| "show me everything for CloudNine" | company estimates | `/chat` has no tool mapped to `get_company_estimates`; model must loop KPI-by-KPI and may hit the 6-iteration limit | The richest endpoint isn't exposed as an MCP tool |
| Typo: "Toatl Revenue" | suggest "Total Revenue ($MM)" | Works — `KpiNotFound.suggestions` | Good; this path is solid |
| "is the guidance bullish?" | decline / redirect | Model may editorialize | No guardrail against opinion/advice framing |

Themes: (a) company resolution is fuzzy-tolerant but **KPI resolution is not**
(exact `ILIKE`, no trigram, no suggestions surfaced conversationally);
(b) there is no explicit slot-filling step, so every ambiguous query's outcome
depends on model judgment; (c) `get_company_estimates` — the natural answer to
"tell me about X" — isn't reachable from chat.

---

## Prioritized improvements (awaiting confirmation, one at a time)

**1. Reuse one long-lived MCP session + shared DB pool per process.**
Removes subprocess spawn, `initialize`/`list_tools`, and pool creation from the
per-question hot path. Biggest single latency win and removes a per-request
failure mode. (§1.1, also helps §1.2 framing.)

**2. Put an auth + rate/size boundary in front of the API and `/chat`.**
Static API key (or bearer token) on all routes, a per-client rate limit on
`/chat`, a `question` length cap, and move the `quarters` clamp into `core/` so
the MCP path inherits it. Closes the open-data and denial-of-wallet exposure.
(§2.1, §2.2, §2.3)

**3. Scope QTD to a single fiscal quarter and define its semantics.**
`get_qtd_estimate` filters to the KPI's current (max) `fiscal_quarter`, returns
only that quarter's snapshots, and reports `fiscal_quarter` from the data model
rather than the last row. Add a one-paragraph definition of what a QTD value
means next to `QtdEstimate`. (§3.1, §3.3)

**4. Move quantitative derivations out of the LLM into `core/`.**
Compute `latest`, `qoq_pct`, `yoy_pct`, and QTD-vs-prior-year in the service
layer; return them as fields; change the system prompt so the model only reads
numbers back, never computes them. (§3.2)

**5. Make tool contracts uniform and KPI resolution forgiving.**
Uniform `{data|error}` envelope + shared `ServiceError→dict` decorator for all
tools; exact resolution via `lower(col) = lower(%s)` (no LIKE wildcards from
user input); trigram fallback + surfaced suggestions for KPI names like
companies already have; expose `get_company_estimates` as an MCP tool; fix the
stale "4 tools" docstrings. (§2.6, §4, §5)

Secondary (not in the top 5, cheap to fold in later): restrict the subprocess
env (§2.5), decide CORS origins explicitly (§2.7), add a TTL cache for
company/KPI lookups (§1.4), fix the `get_company_estimates` N+1 (§1.3).
