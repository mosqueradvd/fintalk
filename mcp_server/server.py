"""FinTalk MCP server.

Exposes 4 tools over the shared core/ layer. Same process boundary as the REST
API in terms of logic (both import core/), but this runs standalone over stdio
so external AI clients (Claude Desktop, Cursor) can connect.

Tool design choices:
  - Tools mirror how an investor-facing agent explores the data:
    discover a company -> see its KPIs -> pull history / QTD.
  - Lookup failures return a structured, recoverable payload
    ({"error", "message", "suggestions"}), never an exception the LLM
    can't reason about.
  - Every call is audited (see audit.py).
"""

from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from core import (
    CompanyNotFound,
    KpiNotFound,
    get_kpi_history,
    get_qtd_estimate,
    list_kpis,
    list_sectors,
    search_companies,
)
from core.config import DEFAULT_HISTORY_QUARTERS
from mcp_server.audit import audited

mcp = FastMCP("fintalk")


@mcp.tool()
@audited
def list_all_sectors() -> list[str]:
    """List every sector covered. Use this to answer "what sectors do you have?"
    or before find_company when the user names a sector you want to confirm."""
    return list_sectors()


@mcp.tool()
@audited
def find_company(query: str) -> list[dict] | dict:
    """Find public companies by name, ticker, or sector (fuzzy match).

    Use this first when the user names a company OR a sector (e.g. "fintech
    companies"). Returns up to 10 matches, each with ticker, name and sector.
    Pass the ticker to the other tools.
    """
    matches = search_companies(query)
    if not matches:
        return {
            "error": "no_matches",
            "message": f"No company matched '{query}'.",
            "suggestions": [],
        }
    return [asdict(c) for c in matches]


@mcp.tool()
@audited
def list_company_kpis(ticker: str) -> list[dict] | dict:
    """List the KPIs tracked for a company, with their units.

    `ticker` must be an exact ticker (use find_company first if unsure).
    """
    try:
        return [asdict(k) for k in list_kpis(ticker)]
    except CompanyNotFound as exc:
        return exc.to_dict()


@mcp.tool()
@audited
def get_history(
    ticker: str, kpi: str, quarters: int = DEFAULT_HISTORY_QUARTERS
) -> dict:
    """Quarterly historical estimates for one KPI (most recent `quarters`).

    `kpi` must be an exact KPI name from list_company_kpis. On a miss the
    response lists the valid KPI names in `suggestions`.
    """
    try:
        return asdict(get_kpi_history(ticker, kpi, quarters=quarters))
    except (CompanyNotFound, KpiNotFound) as exc:
        return exc.to_dict()


@mcp.tool()
@audited
def get_qtd(ticker: str, kpi: str) -> dict:
    """Quarter-to-date estimate series for one KPI (latest snapshot + history).

    Use alongside get_history to compare intra-quarter pace vs. prior quarters.
    """
    try:
        return asdict(get_qtd_estimate(ticker, kpi))
    except (CompanyNotFound, KpiNotFound) as exc:
        return exc.to_dict()


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
