from __future__ import annotations

from uuid import UUID, uuid4

from .observability import CORRELATION_ID


def _correlation_id(request) -> str:
    supplied = str(request.headers.get("X-Request-ID") or "").strip()
    try:
        return str(UUID(supplied)) if supplied else str(uuid4())
    except ValueError:
        return str(uuid4())


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = _correlation_id(request)
        request.correlation_id = correlation_id
        token = CORRELATION_ID.set(correlation_id)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = correlation_id
            return response
        finally:
            CORRELATION_ID.reset(token)
