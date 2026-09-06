"""Runtime configuration for the shared service layer."""

import os

# Postgres DSN. Matches db/docker-compose.yml defaults for local dev.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://fintalk:fintalk@localhost:5432/fintalk"
)

# Default number of quarters returned by get_kpi_history.
DEFAULT_HISTORY_QUARTERS = 8

# Hard bounds for the `quarters` argument of get_kpi_history. Enforced in core/
# so *every* caller (REST and MCP) inherits the same limit — an LLM-driven MCP
# client must not be able to ask for an unbounded row count. (OWASP LLM10)
MIN_HISTORY_QUARTERS = 1
MAX_HISTORY_QUARTERS = 40

# Trigram similarity threshold below which a fuzzy match is ignored.
FUZZY_MATCH_THRESHOLD = 0.2
