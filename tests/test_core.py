"""Core service layer — runs against the loaded sample DB.

Skips automatically if Postgres isn't reachable.
"""

import pytest

from core import (
    CompanyNotFound,
    KpiNotFound,
    get_kpi_history,
    get_qtd_estimate,
    list_kpis,
    search_companies,
)
from core.db import query

try:
    query("SELECT 1")
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="Postgres not reachable")


def test_fuzzy_search_matches_by_partial_name():
    tickers = {c.ticker for c in search_companies("stream")}
    assert "STRM" in tickers  # StreamWave Entertainment


def test_history_is_chronological_and_capped():
    hist = get_kpi_history("IGC", "Total Revenue ($MM)", quarters=4)
    assert len(hist.points) == 4
    starts = [p.period_start for p in hist.points]
    assert starts == sorted(starts)


def test_qtd_returns_latest_snapshot_last():
    qtd = get_qtd_estimate("IGC", "Total Revenue ($MM)")
    assert qtd.latest.as_of_date == qtd.snapshots[-1].as_of_date
    assert qtd.latest.as_of_date >= qtd.snapshots[0].as_of_date


def test_unknown_company_raises_with_suggestions():
    with pytest.raises(CompanyNotFound) as exc:
        list_kpis("NOPExx")
    assert exc.value.to_dict()["error"] == "company_not_found"
    assert exc.value.suggestions  # near-miss tickers offered


def test_unknown_kpi_suggests_valid_names():
    with pytest.raises(KpiNotFound) as exc:
        get_kpi_history("IGC", "Revenu")
    assert "Total Revenue ($MM)" in exc.value.suggestions
