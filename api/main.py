"""FastAPI REST API — a thin adapter over core/.

Responsibilities kept here (and nowhere else):
  - HTTP routing and query-param parsing
  - translating ServiceError -> HTTP status + JSON body
  - opening/closing the DB pool with the app lifecycle

All data logic lives in core/. Handlers are one-liners on purpose.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chat import run_chat
from core import (
    ServiceError,
    get_company_estimates,
    get_kpi_history,
    get_qtd_estimate,
    list_companies,
    list_kpis,
    list_sectors,
    search_companies,
)
from core.db import close_pool, get_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_pool()  # fail fast if Postgres is unreachable
    yield
    close_pool()


app = FastAPI(title="FinTalk API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(ServiceError)
async def _service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/sectors")
def sectors() -> list[str]:
    return list_sectors()


@app.get("/companies")
def companies(
    q: str | None = Query(None, description="fuzzy search by name or ticker"),
    sector: str | None = Query(None),
) -> list[dict]:
    result = search_companies(q) if q else list_companies(sector=sector)
    return [asdict(c) for c in result]


@app.get("/companies/{ticker}/kpis")
def company_kpis(ticker: str) -> list[dict]:
    return [asdict(k) for k in list_kpis(ticker)]


@app.get("/companies/{ticker}/estimates")
def company_estimates(ticker: str) -> dict:
    """All KPI estimates for a company: quarterly history + current QTD."""
    return asdict(get_company_estimates(ticker))


@app.get("/companies/{ticker}/history")
def kpi_history(
    ticker: str,
    kpi: str = Query(..., description="exact KPI name, e.g. 'Total Revenue ($MM)'"),
    quarters: int = Query(8, ge=1, le=40),
) -> dict:
    return asdict(get_kpi_history(ticker, kpi, quarters=quarters))


@app.get("/companies/{ticker}/qtd")
def kpi_qtd(ticker: str, kpi: str = Query(...)) -> dict:
    return asdict(get_qtd_estimate(ticker, kpi))


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(req: ChatRequest) -> dict:
    """Natural-language Q&A. The LLM answers by calling the MCP tools;
    the response includes the full tool-call trace for the UI panel."""
    return asdict(await run_chat(req.question))
