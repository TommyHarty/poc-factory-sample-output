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
