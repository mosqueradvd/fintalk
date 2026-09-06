"""Runtime configuration for the shared service layer."""

import os

# Postgres DSN. Matches db/docker-compose.yml defaults for local dev.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://fintalk:fintalk@localhost:5432/fintalk"
)

# Default number of quarters returned by get_kpi_history.
DEFAULT_HISTORY_QUARTERS = 8

# Trigram similarity threshold below which a fuzzy match is ignored.
FUZZY_MATCH_THRESHOLD = 0.2
