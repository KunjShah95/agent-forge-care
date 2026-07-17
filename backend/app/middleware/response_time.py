"""
Response time logging middleware — records duration for every HTTP request.

Logs structured JSON with method, path, status code, duration in ms, and
request ID so slow endpoints can be identified quickly in production.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agentforge.perf")


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """Adds ``X-Response-Time`` header and logs request duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # Only log slow requests (>500ms) or errors (>=400) to avoid log noise
        if duration_ms > 500 or response.status_code >= 400:
            from app.middleware.request_id import request_id_var
            logger.info(
                "%s %s -> %d (%sms) [rid=%s]",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id_var.get(""),
            )

        return response
