# core/ — shared service layer

Pure functions imported by **both** the REST API and the MCP tools. One place
for SQL and business logic; no MCP→REST→DB hop.

| File | Responsibility |
|------|----------------|
| `config.py`  | env-driven settings (`DATABASE_URL`, defaults) |
| `db.py`      | connection pool + parameterized `query()` helpers — the only place SQL runs |
| `errors.py`  | `ServiceError` hierarchy with `to_dict()` / `http_status` |
| `models.py`  | dataclass return shapes (framework-agnostic) |
| `service.py` | the public functions |

## Public API

```python
search_companies(q, limit=10)          -> list[Company]
list_companies(sector=None)             -> list[Company]
list_sectors()                          -> list[str]
list_kpis(ticker)                       -> list[Kpi]          # raises CompanyNotFound
get_kpi_history(ticker, kpi, quarters=8)-> KpiHistory         # raises CompanyNotFound / KpiNotFound
get_qtd_estimate(ticker, kpi)           -> QtdEstimate        # raises CompanyNotFound / KpiNotFound
get_company_estimates(ticker)           -> CompanyEstimates   # raises CompanyNotFound
```

Lookup misses raise a recoverable error carrying `suggestions` (near-miss
tickers, or the list of valid KPI names) so an LLM caller can retry.

## Security boundary

The LLM never emits SQL. It calls typed functions; every query in `db.py` is
parameterized. Invalid input yields a structured error, never an injection path.
