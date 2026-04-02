"""
FastAPI middleware for tenant isolation and audit logging.
"""

from collections import defaultdict, deque
import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import get_settings

logger = logging.getLogger("privategpt.middleware")


class TenantMiddleware(BaseHTTPMiddleware):
    """Extracts tenant context from JWT and injects into request state."""

    async def dispatch(self, request: Request, call_next):
        # Generate a unique request ID for tracing
        request.state.request_id = str(uuid.uuid4())
        request.state.tenant_id = None

        # Extract tenant from auth header if present
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from core.security import decode_access_token
                token = auth_header.split(" ", 1)[1]
                payload = decode_access_token(token)
                request.state.tenant_id = payload.get("org_id")
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role")
            except Exception:
                pass  # Auth failures handled by route dependencies

        response = await call_next(request)
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs every API request for audit trail compliance."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        request_id = getattr(request.state, "request_id", "unknown")
        tenant_id = getattr(request.state, "tenant_id", "anonymous")

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"| tenant={tenant_id} | status={response.status_code} "
            f"| duration={duration:.3f}s"
        )

        response.headers["X-Request-ID"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-tenant rate limiter for API protection."""

    def __init__(self, app):
        super().__init__(app)
        self._requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health"} or request.url.path.startswith("/docs"):
            return await call_next(request)

        settings = get_settings()
        limit = settings.rate_limit_requests_per_minute
        now = time.time()

        tenant_id = getattr(request.state, "tenant_id", None)
        auth_header = request.headers.get("authorization", "")
        client_host = request.client.host if request.client else "anonymous"
        identity = tenant_id or auth_header or client_host
        key = f"{identity}:{request.url.path}"
        bucket = self._requests[key]

        while bucket and now - bucket[0] > 60:
            bucket.popleft()

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded. Maximum {limit} requests per minute "
                        "for this tenant/path."
                    )
                },
            )

        bucket.append(now)
        return await call_next(request)
