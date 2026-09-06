"""Pure service functions shared by the REST API and the MCP tools.

Design notes:
  - Every function takes plain args and returns dataclasses (or raises a
    ServiceError). No HTTP, no MCP, no LLM concepts leak in here.
  - Company/KPI lookups are fuzzy-tolerant: on a miss we raise a *recoverable*
    error carrying ``suggestions`` so the caller (often an LLM) can retry.
"""

from __future__ import annotations

from .config import DEFAULT_HISTORY_QUARTERS, FUZZY_MATCH_THRESHOLD
from .db import query, query_one
from .errors import CompanyNotFound, KpiNotFound
from .models import (
    Company,
    CompanyEstimates,
    CompanyKpiEstimates,
    Kpi,
    KpiHistory,
    QtdEstimate,
    QtdSnapshot,
    QuarterPoint,
)

# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def list_sectors() -> list[str]:
    rows = query("SELECT DISTINCT sector FROM companies ORDER BY sector")
    return [r["sector"] for r in rows]


def search_companies(q: str, limit: int = 10) -> list[Company]:
    """Fuzzy search by name or ticker (substring match OR trigram similarity)."""
    rows = query(
        """
        SELECT ticker, name, sector,
               GREATEST(similarity(name, %(q)s),
                        similarity(ticker, %(q)s)) AS score
        FROM companies
        WHERE name ILIKE %(like)s
           OR ticker ILIKE %(like)s
           OR similarity(name, %(q)s) > %(threshold)s
           OR similarity(ticker, %(q)s) > %(threshold)s
        ORDER BY score DESC, name ASC
        LIMIT %(limit)s
        """,
        {
            "q": q,
            "like": f"%{q}%",
            "threshold": FUZZY_MATCH_THRESHOLD,
            "limit": limit,
        },
    )
    return [Company(r["ticker"], r["name"], r["sector"]) for r in rows]


def list_companies(sector: str | None = None) -> list[Company]:
    if sector:
        rows = query(
            "SELECT ticker, name, sector FROM companies "
            "WHERE sector ILIKE %s ORDER BY name",
            (sector,),
        )
    else:
        rows = query("SELECT ticker, name, sector FROM companies ORDER BY name")
    return [Company(r["ticker"], r["name"], r["sector"]) for r in rows]


# --------------------------------------------------------------------------- #
# Resolution helpers (raise recoverable errors on a miss)
# --------------------------------------------------------------------------- #


def _resolve_company(ticker: str) -> Company:
    row = query_one(
        "SELECT ticker, name, sector FROM companies WHERE ticker ILIKE %s",
        (ticker,),
    )
    if row:
        return Company(row["ticker"], row["name"], row["sector"])

    suggestions = [
        {"ticker": c.ticker, "name": c.name}
        for c in search_companies(ticker, limit=5)
    ]
    raise CompanyNotFound(
        f"No company found for '{ticker}'.", suggestions=suggestions
    )


def _resolve_kpi(company: Company, kpi_name: str) -> tuple[int, Kpi]:
    row = query_one(
        """
        SELECT k.id, k.name, k.unit
        FROM kpis k
        JOIN companies c ON c.id = k.company_id
        WHERE c.ticker = %s AND k.name ILIKE %s
        """,
        (company.ticker, kpi_name),
    )
    if row:
        return row["id"], Kpi(row["name"], row["unit"])

    available = [k.name for k in list_kpis(company.ticker)]
    raise KpiNotFound(
        f"'{company.ticker}' has no KPI named '{kpi_name}'.",
        suggestions=available,
    )


# --------------------------------------------------------------------------- #
# KPI data
# --------------------------------------------------------------------------- #


def list_kpis(ticker: str) -> list[Kpi]:
    company = _resolve_company(ticker)
    rows = query(
        """
        SELECT k.name, k.unit
        FROM kpis k
        JOIN companies c ON c.id = k.company_id
        WHERE c.ticker = %s
        ORDER BY k.name
        """,
        (company.ticker,),
    )
    return [Kpi(r["name"], r["unit"]) for r in rows]


def get_kpi_history(
    ticker: str, kpi: str, quarters: int | None = DEFAULT_HISTORY_QUARTERS
) -> KpiHistory:
    """Quarterly history, most recent ``quarters`` (or all when ``quarters`` is None)."""
    company = _resolve_company(ticker)
    kpi_id, kpi_obj = _resolve_kpi(company, kpi)

    rows = query(
        """
        SELECT fiscal_quarter, period_start, period_end, value
        FROM quarterly_estimates
        WHERE kpi_id = %s
        ORDER BY period_start DESC
        LIMIT %s
        """,
        (kpi_id, quarters),  # psycopg sends None as SQL NULL -> LIMIT ALL
    )
    points = [
        QuarterPoint(
            r["fiscal_quarter"], r["period_start"], r["period_end"], float(r["value"])
        )
        for r in reversed(rows)  # back to chronological order
    ]
    return KpiHistory(company=company, kpi=kpi_obj, points=points)


def get_qtd_estimate(ticker: str, kpi: str) -> QtdEstimate:
    company = _resolve_company(ticker)
    kpi_id, kpi_obj = _resolve_kpi(company, kpi)

    rows = query(
        """
        SELECT fiscal_quarter, as_of_date, value
        FROM qtd_estimates
        WHERE kpi_id = %s
        ORDER BY as_of_date ASC
        """,
        (kpi_id,),
    )
    if not rows:
        raise KpiNotFound(
            f"No QTD estimate available for {company.ticker} / {kpi_obj.name}."
        )

    snapshots = [QtdSnapshot(r["as_of_date"], float(r["value"])) for r in rows]
    return QtdEstimate(
        company=company,
        kpi=kpi_obj,
        fiscal_quarter=rows[-1]["fiscal_quarter"],
        latest=snapshots[-1],
        snapshots=snapshots,
    )


def get_company_estimates(ticker: str) -> CompanyEstimates:
    """Everything for one company: history + current QTD for every KPI.

    Backs the REST endpoint that returns all KPI estimates for a company.
    """
    company = _resolve_company(ticker)
    result: list[CompanyKpiEstimates] = []

    for kpi in list_kpis(company.ticker):
        history = get_kpi_history(company.ticker, kpi.name, quarters=None).points
        try:
            qtd = get_qtd_estimate(company.ticker, kpi.name)
        except KpiNotFound:
            qtd = None
        result.append(CompanyKpiEstimates(kpi=kpi, history=history, qtd=qtd))

    return CompanyEstimates(company=company, kpis=result)
