"""Tool-call audit logging.

Every MCP tool call is logged as one structured JSON line (tool, args, outcome,
result summary, latency) so agent behaviour can be inspected after the fact.

Uses core.obs, so lines land on stderr, logs/app.log and the dedicated
append-only logs/mcp_audit.log. stdout stays reserved for the MCP protocol.
"""

from __future__ import annotations

import functools
import inspect
import time
from datetime import date, datetime
from typing import Any, Callable

from core.errors import ServiceError
from core.obs import get_logger, log_event

_log = get_logger("mcp.audit", audit_file="mcp_audit.log")


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
        return result if "error" in result else {"keys": sorted(result.keys())}
    return result


def audited(fn: Callable) -> Callable:
    """Decorator: log one audit line per MCP tool call."""

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

        try:
            result = fn(*args, **kwargs)
        except ServiceError as exc:  # tools normally catch these; log + re-raise
            log_event(
                _log,
                "tool_call",
                tool=fn.__name__,
                args=_jsonable(call_args),
                outcome="error",
                result=exc.to_dict(),
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            raise

        outcome = "error" if isinstance(result, dict) and "error" in result else "ok"
        log_event(
            _log,
            "tool_call",
            tool=fn.__name__,
            args=_jsonable(call_args),
            outcome=outcome,
            result=_summarize(result),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        return result

    return wrapper
