"""Redis-backed fixed-window rate limiting, used as a FastAPI dependency.

Counters live in Redis so the limit holds across every API worker and replica.
If Redis is unreachable the request is allowed (fail open) and a warning is
logged: a cache outage should not lock every user out of authentication.
"""

# No `from __future__ import annotations` here: FastAPI must see the real
# `Request` type on `__call__` to inject it into this class-based dependency.
import logging
import time

from fastapi import HTTPException, Request, status

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, scope: str, limit: int, window_seconds: int = 60) -> None:
        self.scope = scope
        self.limit = limit
        self.window_seconds = window_seconds

    def _key(self, client_id: str, now: float) -> tuple[str, int]:
        window = int(now // self.window_seconds)
        retry_after = self.window_seconds - int(now % self.window_seconds)
        return f"ratelimit:{self.scope}:{client_id}:{window}", max(retry_after, 1)

    async def hit(self, redis, client_id: str, now: float | None = None) -> None:
        """Count one request; raise HTTP 429 once the window's limit is exceeded."""
        key, retry_after = self._key(client_id, time.time() if now is None else now)
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self.window_seconds)
        except Exception:  # noqa: BLE001 - any Redis failure means fail open
            logger.warning("rate limiter unavailable, allowing request", extra={"scope": self.scope})
            return
        if count > self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    async def __call__(self, request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return
        client_id = request.client.host if request.client else "unknown"
        await self.hit(redis, client_id)


def auth_rate_limiter(scope: str) -> RateLimiter:
    return RateLimiter(scope=scope, limit=get_settings().auth_rate_limit_per_minute, window_seconds=60)
