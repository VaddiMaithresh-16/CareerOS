"""Request-id tracing + optional API-key auth + in-memory rate limiting.

Auth is opt-in: set API_KEY in env to require an X-API-Key header on every
request. No API_KEY set -> open, same as before (dev-friendly default, but
now there's a real switch to flip for prod instead of nothing at all).

Rate limiting is a simple in-memory sliding window per client IP — good
enough for a single-process deploy; swap for a Redis-backed limiter if you
run multiple workers/instances and need a shared counter.
"""

import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("careeros")

_request_counts: dict[str, deque] = defaultdict(deque)
_RATE_LIMIT_WINDOW_SECONDS = 60


def _warn_if_unsafe_rate_limit_config() -> None:
    """Log a warning if multi-worker deployment with in-memory rate limiting."""
    # In production with workers > 1, in-memory rate limiting is per-process
    # and won't be shared across workers. This is a common misconfiguration.
    if settings.rate_limit_per_minute and settings.app_env == "production":
        import os
        # Granian sets WORKER_COUNT env or can be detected via process count
        # We can't reliably detect worker count here, so warn if API_KEY is set
        # (indicating prod intent) and rate limiting is enabled
        if settings.api_key:
            logger.warning(
                "Rate limiting enabled with in-memory backend in production. "
                "With multiple workers, each worker has a separate counter. "
                "Use a Redis-backed limiter for shared rate limiting."
            )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, logs method/path/status/duration for every call."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
            request_id, request.method, request.url.path, response.status_code, duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.limit = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = _request_counts[client_ip]

        while window and now - window[0] > _RATE_LIMIT_WINDOW_SECONDS:
            window.popleft()

        if len(window) >= self.limit:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning("request_id=%s rate_limited ip=%s", request_id, client_ip)
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded, try again shortly"})

        window.append(now)
        return await call_next(request)


async def require_api_key(request: Request):
    """FastAPI dependency. No-op when API_KEY isn't configured (dev default)."""
    if not settings.api_key:
        return
    provided = request.headers.get("X-API-Key")
    if provided != settings.api_key:
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")
