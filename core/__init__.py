"""Shared service layer.

Imported directly by both the REST API and the MCP tools so query/business
logic lives in exactly one place (no MCP -> REST -> DB double hop).
"""

from .errors import CompanyNotFound, KpiNotFound, ServiceError
from .service import (
    get_company_estimates,
    get_kpi_history,
    get_qtd_estimate,
    list_companies,
    list_kpis,
    list_sectors,
    search_companies,
)

__all__ = [
    "ServiceError",
    "CompanyNotFound",
    "KpiNotFound",
    "search_companies",
    "list_companies",
    "list_sectors",
    "list_kpis",
    "get_kpi_history",
    "get_qtd_estimate",
    "get_company_estimates",
]
