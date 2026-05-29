import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("agentforge")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        logger.info(
            "%s %s -> %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
        )
        return response
