# Code Implementation: Rate Limiting Strategies

## Overview

In this guide, we will implement a rate limiting strategy using FastAPI and SlowAPI to mitigate brute force and denial of service attacks. By the end of this walkthrough, you will have a working application that limits the number of login attempts per IP address, ensuring enhanced security for your API endpoints.

## Prerequisites

- Python 3.11 or higher
- Key packages: FastAPI, SlowAPI, Pydantic
- No external services are required for this implementation.

## Implementation Steps

## Step 1: Define Domain Models

**File**: `app/models/schemas.py`

This file contains the Pydantic models used for request and response validation. The `LoginRequest` model captures the username and password, while the `LoginResponse` model returns an access token. These models ensure that the data structure is consistent and validated.

```python
from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_env: str
```

## Step 2: Implement Rate Limiting Service

**File**: `app/services/rate_limiter.py`

This file sets up the rate limiting logic using SlowAPI. The `Limiter` is configured to limit requests based on the client's IP address. The `LOGIN_RATE_LIMIT` is defined to allow 5 login attempts per minute per IP, which helps prevent brute force attacks.

```python
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_ipaddr

# Use get_ipaddr so tests can control the rate limit bucket via X-Forwarded-For header.
# In production, this reads the real client IP from X-Forwarded-For or request.client.host.
limiter = Limiter(key_func=get_ipaddr)

# Rate limit for the /login endpoint — 5 attempts per minute per IP.
# This mitigates brute force attacks against the authentication endpoint.
LOGIN_RATE_LIMIT = "5/minute"
```

## Step 3: Define API Routes

**File**: `app/api/routes.py`

This file defines the API endpoints using FastAPI. The `/login` endpoint is protected with a rate limit decorator, ensuring that requests exceeding the defined limit return a 429 status code. The endpoint returns a demo token without actual credential validation, focusing on demonstrating the rate limiting.

```python
from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.schemas import LoginRequest, LoginResponse
from app.services.rate_limiter import LOGIN_RATE_LIMIT, limiter

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    """Authenticate a user.

    Rate-limited to LOGIN_RATE_LIMIT per IP to prevent brute force attacks.
    In this POC the credentials are not validated — the focus is demonstrating
    that the rate limit is enforced and returns 429 when exceeded.
    """
    # Real implementations would verify credentials against a database here.
    return LoginResponse(access_token="demo-token")
```

## Step 4: Setup FastAPI Application

**File**: `app/main.py`

This file initializes the FastAPI application and integrates the rate limiting middleware. It includes the router with the login endpoint and sets up exception handling for rate limit exceedance.

```python
from __future__ import annotations

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import router
from app.services.rate_limiter import limiter
from core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

# Attach limiter to app state and register the 429 exception handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(router)
```

## Step 5: Configure Tests

**File**: `tests/conftest.py`

This file sets up the test client for asynchronous testing with HTTPX. It ensures that the rate limiter's storage is reset before each test, isolating test cases from each other.

```python
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:  # type: ignore[misc]
    """Async HTTP client wired directly to the ASGI app."""
    # Reset the in-memory rate limit storage before each test so tests are isolated
    # from each other regardless of how get_ipaddr resolves the client IP.
    from app.services.rate_limiter import limiter
    limiter._storage.reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
```

**File**: `tests/test_api.py`

This file contains tests for the login endpoint, verifying that the rate limit is enforced and that the endpoint returns the expected responses.

```python
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
```

**File**: `tests/test_health.py`

This file tests the health endpoint to ensure it returns the expected status and application information.

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "app_name" in data
    assert "app_env" in data
    assert data["status"] == "ok"
```

**File**: `tests/test_rate_limiter.py`

This file contains unit tests for the rate limiter configuration, ensuring that the limiter is correctly set up and the rate limit values are as expected.

```python
from __future__ import annotations

from app.services.rate_limiter import LOGIN_RATE_LIMIT, limiter


def test_limiter_is_configured() -> None:
    """Limiter instance is created and attached to the module."""
    assert limiter is not None


def test_login_rate_limit_value() -> None:
    """LOGIN_RATE_LIMIT is a non-empty string in the expected format."""
    assert isinstance(LOGIN_RATE_LIMIT, str)
    assert "/" in LOGIN_RATE_LIMIT, "Rate limit must be in 'N/period' format"


def test_login_rate_limit_per_minute() -> None:
    """Rate limit for /login is expressed per minute."""
    assert LOGIN_RATE_LIMIT.endswith("/minute"), (
        "Login should be rate-limited per minute to mitigate brute force"
    )


def test_login_rate_limit_count() -> None:
    """The allowed request count per minute is a positive integer."""
    count_str, _ = LOGIN_RATE_LIMIT.split("/")
    count = int(count_str)
    assert count > 0
```

## Step 6: Configure Project Dependencies

**File**: `pyproject.toml`

This file specifies the project's dependencies, including FastAPI, SlowAPI, and testing libraries. These dependencies are essential for running the application and tests.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "poc-starter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic-settings",
    "slowapi",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "core*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Verification

To confirm the POC is working:

- Run the application using: `./scripts/run.sh`
- Execute the tests with: `./scripts/test.sh`
- Test the `/login` endpoint by making POST requests. Expect a 200 status code for the first 5 requests and a 429 status code for subsequent requests from the same IP within a minute.

## Key Takeaway

Implementing rate limiting is a crucial strategy for enhancing the security of API endpoints. By controlling the number of requests from a single IP, we can effectively mitigate the risk of brute force attacks and ensure the stability and reliability of the service.