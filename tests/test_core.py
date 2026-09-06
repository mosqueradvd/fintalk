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
from core.db import query, query_one

try:
    query("SELECT 1")
    DB_UP = True
except Exception:
    DB_UP = False

pytestmark = pytest.mark.skipif(not DB_UP, reason="Postgres not reachable")


def test_fuzzy_search_matches_by_partial_name():
    tickers = {c.ticker for c in search_companies("stream")}
    assert "STRM" in tickers  # StreamWave Entertainment


def test_fuzzy_search_matches_by_sector():
    results = search_companies("fintech")
    assert results and results[0].sector == "Fintech"  # exact match ranks first


def test_history_is_chronological_and_capped():
    hist = get_kpi_history("IGC", "Total Revenue ($MM)", quarters=4)
    assert len(hist.points) == 4
    starts = [p.period_start for p in hist.points]
    assert starts == sorted(starts)


def test_qtd_returns_latest_snapshot_last():
    qtd = get_qtd_estimate("IGC", "Total Revenue ($MM)")
    assert qtd.latest.as_of_date == qtd.snapshots[-1].as_of_date
    assert qtd.latest.as_of_date >= qtd.snapshots[0].as_of_date


def test_history_quarters_is_clamped_to_max():
    # Ask for far more than the cap; core must not return an unbounded window.
    hist = get_kpi_history("IGC", "Total Revenue ($MM)", quarters=10_000)
    assert len(hist.points) <= 40


def test_like_wildcards_do_not_resolve_a_company():
    # '%' / '_' are LIKE metacharacters; they must not match an arbitrary row.
    with pytest.raises(CompanyNotFound):
        list_kpis("%")
    with pytest.raises(CompanyNotFound):
        list_kpis("_GC")


def test_qtd_is_scoped_to_one_fiscal_quarter():
    qtd = get_qtd_estimate("IGC", "Total Revenue ($MM)")
    quarters = {
        query_one(
            "SELECT fiscal_quarter FROM qtd_estimates "
            "WHERE as_of_date = %s LIMIT 1",
            (s.as_of_date,),
        )["fiscal_quarter"]
        for s in qtd.snapshots
    }
    assert len(quarters) == 1
    assert qtd.fiscal_quarter in quarters


def test_unknown_company_raises_with_suggestions():
    with pytest.raises(CompanyNotFound) as exc:
        list_kpis("NOPExx")
    assert exc.value.to_dict()["error"] == "company_not_found"
    assert exc.value.suggestions  # near-miss tickers offered


def test_unknown_kpi_suggests_valid_names():
    with pytest.raises(KpiNotFound) as exc:
        get_kpi_history("IGC", "Revenu")
    assert "Total Revenue ($MM)" in exc.value.suggestions
