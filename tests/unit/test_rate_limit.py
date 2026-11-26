import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds


class BrokenRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis down")


@pytest.mark.asyncio
async def test_allows_requests_up_to_the_limit() -> None:
    limiter, redis = RateLimiter("login", limit=3, window_seconds=60), FakeRedis()
    for _ in range(3):
        await limiter.hit(redis, "1.2.3.4", now=120.0)
    assert list(redis.ttls.values()) == [60]


@pytest.mark.asyncio
async def test_rejects_with_429_and_retry_after_once_exceeded() -> None:
    limiter, redis = RateLimiter("login", limit=2, window_seconds=60), FakeRedis()
    await limiter.hit(redis, "1.2.3.4", now=130.0)
    await limiter.hit(redis, "1.2.3.4", now=130.0)
    with pytest.raises(HTTPException) as exc:
        await limiter.hit(redis, "1.2.3.4", now=130.0)
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "50"


@pytest.mark.asyncio
async def test_limits_are_per_client_and_per_window() -> None:
    limiter, redis = RateLimiter("login", limit=1, window_seconds=60), FakeRedis()
    await limiter.hit(redis, "1.1.1.1", now=10.0)
    await limiter.hit(redis, "2.2.2.2", now=10.0)  # different client
    await limiter.hit(redis, "1.1.1.1", now=70.0)  # next window


@pytest.mark.asyncio
async def test_fails_open_when_redis_is_unavailable() -> None:
    await RateLimiter("login", limit=1).hit(BrokenRedis(), "1.2.3.4")


def test_works_as_a_route_dependency() -> None:
    """Guards the FastAPI wiring: the limiter must receive the Request, not a query param."""
    app = FastAPI()
    app.state.redis = FakeRedis()

    @app.post("/login", dependencies=[Depends(RateLimiter("login", limit=2))])
    def login() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert [client.post("/login").status_code for _ in range(3)] == [200, 200, 429]
