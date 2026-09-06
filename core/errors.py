"""Typed, recoverable errors.

Core functions *raise* these. Adapters translate them:
  - the MCP tools return ``err.to_dict()`` so the LLM can recover
    (e.g. retry with a suggested ticker) instead of seeing a raw 404;
  - the REST API maps ``err.http_status`` + ``err.to_dict()`` to a response.
"""

from __future__ import annotations


class ServiceError(Exception):
    code: str = "service_error"
    http_status: int = 400

    def __init__(self, message: str, *, suggestions: list | None = None):
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []

    def to_dict(self) -> dict:
        payload: dict = {"error": self.code, "message": self.message}
        if self.suggestions:
            payload["suggestions"] = self.suggestions
        return payload


class CompanyNotFound(ServiceError):
    code = "company_not_found"
    http_status = 404


class KpiNotFound(ServiceError):
    code = "kpi_not_found"
    http_status = 404
