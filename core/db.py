"""Thin Postgres access helpers.

The service layer only ever runs parameterized queries through these helpers —
there is no string interpolation of user/LLM input into SQL anywhere in core/.
That is the security boundary between the LLM and the data.
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import DATABASE_URL

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Lazily create a process-wide connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Close the pool (call on app shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def query(sql: str, params: dict[str, Any] | tuple = ()) -> list[dict]:
    """Run a read query and return all rows as dicts."""
    with get_pool().connection() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: dict[str, Any] | tuple = ()) -> dict | None:
    """Run a read query and return the first row, or None."""
    with get_pool().connection() as conn:
        return conn.execute(sql, params).fetchone()
