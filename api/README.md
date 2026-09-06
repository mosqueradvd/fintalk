# api/ — REST API

Thin HTTP adapter over [`core/`](../core). Handlers just parse params, call a
core function, and `asdict()` the result. `ServiceError` is translated to its
`http_status` + `to_dict()` body by one exception handler.

## Run

```bash
export DATABASE_URL=postgresql://fintalk:fintalk@localhost:5432/fintalk
uvicorn api.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

## Endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | liveness |
| `GET /sectors` | distinct sectors |
| `GET /companies?q=&sector=` | fuzzy search (`q`) or list, optionally filtered by `sector` |
| `GET /companies/{ticker}/kpis` | KPIs for a company |
| `GET /companies/{ticker}/estimates` | all KPI history + current QTD for a company |
| `GET /companies/{ticker}/history?kpi=&quarters=8` | quarterly history for one KPI |
| `GET /companies/{ticker}/qtd?kpi=` | QTD snapshot series for one KPI |

KPI is a query param (not a path segment) because names contain spaces and
parentheses, e.g. `Total Revenue ($MM)`.

## Errors

`404` with `{"error": "...", "message": "...", "suggestions": [...]}` for
unknown ticker / KPI — same shape the MCP tools return.
