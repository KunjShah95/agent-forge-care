"""
Request ID middleware — attaches a unique correlation ID to every request.

This enables distributed tracing across services and makes it possible to
correlate frontend logs, API logs, and background task logs for a single user
action.  The ID is returned in the ``X-Request-ID`` response header so the
frontend can include it in error reports.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable so any async code downstream can access the current request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that generates a UUID4 for each request and attaches it to the
    response headers and the ``request_id_var`` context variable."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept incoming X-Request-ID from the client (e.g. frontend) if present,
        # otherwise generate a new one.
        incoming_id = request.headers.get("x-request-id", "")
        rid = incoming_id if incoming_id else str(uuid.uuid4())

        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = rid
        return response
