"""Tool-call audit logging.

Every MCP tool call is logged as one structured JSON line: tool name, args,
outcome (ok/error), a short result summary, and latency. This is what lets us
inspect agent behaviour after the fact (assignment requirement).

IMPORTANT: on a stdio MCP server, stdout carries the protocol. Audit logs go to
stderr and to logs/mcp_audit.log — never stdout.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from core.errors import ServiceError

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("mcp.audit")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.propagate = False  # don't double-log via the root/Rich handler
    logger.addHandler(logging.StreamHandler())  # stderr
    logger.addHandler(logging.FileHandler(_LOG_DIR / "mcp_audit.log"))


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _summarize(result: Any) -> Any:
    """Keep the log line small: counts/keys instead of full payloads."""
    if isinstance(result, list):
        return {"count": len(result)}
    if isinstance(result, dict):
        if "error" in result:
            return result
        return {"keys": sorted(result.keys())}
    return result


def audited(fn: Callable) -> Callable:
    """Decorator: log one JSON line per call of an MCP tool."""

    sig = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            call_args = dict(bound.arguments)
        except TypeError:
            call_args = {"args": list(args), "kwargs": kwargs}
        record: dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tool": fn.__name__,
            "args": _jsonable(call_args),
        }
        try:
            result = fn(*args, **kwargs)
        except ServiceError as exc:  # tools normally catch these; log + re-raise
            record["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            record.update(outcome="error", result=exc.to_dict())
            logger.info(json.dumps(record))
            raise

        record["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        outcome = "error" if isinstance(result, dict) and "error" in result else "ok"
        record.update(outcome=outcome, result=_summarize(result))
        logger.info(json.dumps(record))
        return result

    return wrapper
