import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("agentforge")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.middleware.request_id import request_id_var

        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        rid = request_id_var.get("")
        logger.info(
            "%s %s -> %d (%.2fms) [rid=%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
            rid,
        )
        return response
