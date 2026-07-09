"""
Audit Logging Middleware — structured logging for sensitive operations.

Logs all state-changing operations (POST, PUT, PATCH, DELETE) with:
- Actor (user ID or IP)
- Action (HTTP method + path)
- Timestamp (ISO 8601)
- Success/failure status + duration

Audit logs are routed to a dedicated structured logger.
"""

import logging
import time
from datetime import UTC, datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("agentforge.audit")

# Endpoints that are NOT logged (health checks, static files, etc.)
_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/api/v1/status"}

# Read-only methods that don't need audit logging
_READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}

# Sensitive paths always logged, even for read-only methods
_SENSITIVE_PATHS = {"/api/v1/auth/", "/api/v1/profile/", "/api/v1/applications/"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Middleware that creates structured audit log entries for state-changing operations."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip non-audited paths and safe read-only operations
        if path in _SKIP_PATHS:
            return await call_next(request)
        if request.method in _READ_ONLY_METHODS and not any(
            path.startswith(s) for s in _SENSITIVE_PATHS
        ):
            return await call_next(request)

        # Extract actor (user or IP)
        actor = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                from jose import jwt as jose_jwt
                payload = jose_jwt.get_unverified_claims(auth.split(" ", 1)[1])
                actor = payload.get("sub") or actor
            except Exception:
                pass

        start = time.time()
        try:
            response = await call_next(request)
            ok = response.status_code < 500
        except Exception:
            ok = False
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            log_entry = {
                "ts": datetime.now(UTC).isoformat(),
                "actor": actor,
                "action": f"{request.method} {path}",
                "status": response.status_code if ok else 500,
                "ok": ok,
                "ms": round(elapsed_ms, 1),
            }
            log_fn = logger.info if ok else logger.warning
            log_fn("audit", extra={"audit": log_entry})

        return response
