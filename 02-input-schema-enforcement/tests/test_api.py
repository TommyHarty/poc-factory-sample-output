from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:  # type: ignore[override]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# /submit-data — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_submission(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "alice_01", "action": "write", "content": "Store report summary"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["validated_action"] == "write"
    assert data["user_id"] == "alice_01"


@pytest.mark.asyncio
async def test_valid_submission_with_tags(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={
            "user_id": "carol",
            "action": "delete",
            "content": "Remove stale session",
            "tags": ["session", "cleanup"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_all_valid_actions(client: AsyncClient) -> None:
    for action in ("read", "write", "delete"):
        response = await client.post(
            "/submit-data",
            json={"user_id": "u1", "action": action, "content": "payload"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /submit-data — Pydantic structural rejections (422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_required_field_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"action": "read", "content": "no user_id"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_action_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "bob", "action": "execute", "content": "try something"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_extra_field_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "bob", "action": "read", "content": "ok", "injected": "extra"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_user_id_characters_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "bad user!", "action": "read", "content": "ok"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_content_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "u1", "action": "read", "content": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_oversized_content_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "u1", "action": "read", "content": "x" * 501},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /submit-data — semantic rejections (400)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sql_injection_in_content_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={
            "user_id": "attacker",
            "action": "write",
            "content": "SELECT * FROM users WHERE 1=1",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_script_injection_in_content_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={
            "user_id": "attacker",
            "action": "write",
            "content": "<script>alert('xss')</script>",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_drop_table_in_content_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={"user_id": "u1", "action": "write", "content": "DROP TABLE sessions"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_tag_format_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/submit-data",
        json={
            "user_id": "carol",
            "action": "read",
            "content": "ok",
            "tags": ["UPPERCASE"],
        },
    )
    assert response.status_code == 400
