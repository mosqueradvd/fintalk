"""Observability primitives shared across the app.

One JSON line per event, to stderr and to logs/app.log. A request id is carried
in a contextvar so every line emitted while handling one HTTP request (or one
chat turn) can be correlated after the fact.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@contextmanager
def request_context(request_id: str | None = None):
    """Bind a request id for the duration of the block.

    If none is given and one is already bound (e.g. set by the API middleware),
    that one is kept so logs stay correlated across the HTTP + chat boundary.
    """
    rid = request_id or (
        request_id_var.get() if request_id_var.get() != "-" else new_request_id()
    )
    token = request_id_var.set(rid)
    try:
        yield rid
    finally:
        request_id_var.reset(token)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "event": record.getMessage(),
        }
        payload.update(_jsonable(getattr(record, "fields", {})))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(name: str, *, audit_file: str | None = None) -> logging.Logger:
    """Return a JSON-line logger (stderr + logs/app.log, plus an optional
    dedicated append-only audit file)."""
    logger = logging.getLogger(name)
    if getattr(logger, "_fintalk_configured", False):
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = _JsonFormatter()

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    app_file = logging.FileHandler(_LOG_DIR / "app.log")
    app_file.setFormatter(fmt)
    logger.addHandler(app_file)

    if audit_file:
        audit = logging.FileHandler(_LOG_DIR / audit_file)
        audit.setFormatter(fmt)
        logger.addHandler(audit)

    logger._fintalk_configured = True  # type: ignore[attr-defined]
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit one structured line: log_event(log, "chat_completed", tools=3, ms=812)."""
    logger.info(event, extra={"fields": fields})
