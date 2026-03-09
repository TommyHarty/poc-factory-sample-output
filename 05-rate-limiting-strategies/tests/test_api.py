from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.rate_limiter import LOGIN_RATE_LIMIT

# Parse the allowed count from the rate limit string (e.g. "5/minute" -> 5).
_LIMIT_COUNT = int(LOGIN_RATE_LIMIT.split("/")[0])

# Each test uses a distinct IP via X-Forwarded-For so tests don't share buckets.
_IP_SUCCESS = "10.0.1.1"
_IP_RATE_LIMITED = "10.0.1.2"
_IP_HEALTH = "10.0.1.3"

_LOGIN_PAYLOAD = {"username": "alice", "password": "secret"}


@pytest.mark.asyncio
async def test_login_returns_token(async_client: AsyncClient) -> None:
    """A single login request succeeds and returns an access token."""
    response = await async_client.post(
        "/login",
        json=_LOGIN_PAYLOAD,
        headers={"X-Forwarded-For": _IP_SUCCESS},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_rate_limit_enforced(async_client: AsyncClient) -> None:
    """Requests up to the limit succeed; the next one receives HTTP 429."""
    headers = {"X-Forwarded-For": _IP_RATE_LIMITED}

    # All requests within the limit should succeed.
    for i in range(_LIMIT_COUNT):
        response = await async_client.post("/login", json=_LOGIN_PAYLOAD, headers=headers)
        assert response.status_code == 200, (
            f"Request {i + 1} of {_LIMIT_COUNT} should succeed, got {response.status_code}"
        )

    # The next request must be rejected.
    response = await async_client.post("/login", json=_LOGIN_PAYLOAD, headers=headers)
    assert response.status_code == 429, (
        f"Expected 429 after exceeding rate limit, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_health_not_rate_limited(async_client: AsyncClient) -> None:
    """/health is accessible many times without triggering a rate limit."""
    headers = {"X-Forwarded-For": _IP_HEALTH}

    for _ in range(_LIMIT_COUNT + 5):
        response = await async_client.get("/health", headers=headers)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(async_client: AsyncClient) -> None:
    """/health returns the expected JSON fields."""
    response = await async_client.get("/health", headers={"X-Forwarded-For": "10.0.1.4"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app_name" in body
    assert "app_env" in body
