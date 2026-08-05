"""API Gateway Rate Limiting Middleware enforcing distributed token bucket limits and HTTP 429 responses."""

from typing import Any, Callable

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.infrastructure.rate_limit.distributed_rate_limiter import (
    DistributedRateLimiter,
)
from app.infrastructure.rate_limit.distributed_rate_limiter import (
    rate_limiter as default_rate_limiter,
)
from app.security.jwt import decode_access_token

logger = structlog.get_logger(__name__)

# Excluded endpoints from strict rate limiting
EXEMPT_PATHS = {"/docs", "/redoc", "/openapi.json", "/health", "/favicon.ico", "/"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware checking per-request token buckets and returning X-RateLimit headers."""

    def __init__(
        self, app: ASGIApp, limiter: DistributedRateLimiter = default_rate_limiter
    ) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Process request against rate limit bucket and append rate limit headers."""
        path = request.url.path
        if path in EXEMPT_PATHS or path.endswith(".png") or path.endswith(".ico"):
            res: Response = await call_next(request)
            return res

        # 1. Identify Requester (IP vs Authenticated User)
        client_ip = request.client.host if request.client else "127.0.0.1"
        identifier = client_ip
        limit_type = "ip"
        user_role = "VIEWER"

        # Extract authorization bearer token if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                role = payload.get("role", "VIEWER")
                if user_id:
                    identifier = str(user_id)
                    limit_type = "user"
                    user_role = str(role)
            except Exception as err:
                logger.debug("rate_limit_token_decode_pass", error=str(err))

        # 2. Check Distributed Rate Limiter
        result = await self.limiter.check_rate_limit(
            identifier=identifier,
            limit_type=limit_type,
            role=user_role,
        )

        # 3. Reject if rate limit exceeded
        if not result.allowed:
            request_id = getattr(request.state, "request_id", "unknown")
            headers = {
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result.reset_seconds),
                "Retry-After": str(result.reset_seconds),
            }
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                        "request_id": request_id,
                    }
                },
            )

        # 4. Process Request and attach Rate Limit Headers to response
        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_seconds)

        return response
