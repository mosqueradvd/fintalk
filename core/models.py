"""Return shapes for the service layer.

Plain dataclasses on purpose: core/ stays framework-agnostic (no pydantic,
no FastAPI import). REST and MCP adapters serialize these with asdict().
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Company:
    ticker: str
    name: str
    sector: str


@dataclass
class Kpi:
    name: str
    unit: str


@dataclass
class QuarterPoint:
    fiscal_quarter: str
    period_start: date
    period_end: date
    value: float


@dataclass
class KpiHistory:
    company: Company
    kpi: Kpi
    points: list[QuarterPoint]  # chronological (oldest first)


@dataclass
class QtdSnapshot:
    as_of_date: date
    value: float


@dataclass
class QtdEstimate:
    company: Company
    kpi: Kpi
    fiscal_quarter: str
    latest: QtdSnapshot
    snapshots: list[QtdSnapshot]  # chronological (oldest first)


@dataclass
class CompanyKpiEstimates:
    kpi: Kpi
    history: list[QuarterPoint]
    qtd: QtdEstimate | None


@dataclass
class CompanyEstimates:
    company: Company
    kpis: list[CompanyKpiEstimates]
