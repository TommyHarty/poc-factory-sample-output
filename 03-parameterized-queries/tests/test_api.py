from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.query_service import QueryService, get_query_service


# ---------------------------------------------------------------------------
# Fixture: isolated in-memory database per test
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_service(monkeypatch: pytest.MonkeyPatch) -> QueryService:
    """Replace the module-level singleton with a fresh in-memory instance."""
    svc = QueryService(db_path=":memory:")

    # Override the FastAPI dependency so routes use this instance.
    app.dependency_overrides[get_query_service] = lambda: svc
    yield svc
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(isolated_service: QueryService) -> AsyncClient:  # noqa: RUF029
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Seed endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed(client: AsyncClient) -> None:
    response = await client.post("/api/seed")
    assert response.status_code == 200
    body = response.json()
    assert body["rows_inserted"] == 3


# ---------------------------------------------------------------------------
# Happy-path SELECT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_select_all_users_after_seed(client: AsyncClient) -> None:
    await client.post("/api/seed")

    response = await client.post(
        "/api/execute-query",
        json={"query": "SELECT username FROM users ORDER BY username", "parameters": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    usernames = [r["username"] for r in body["rows"]]
    assert usernames == ["alice", "bob", "carol"]


@pytest.mark.asyncio
async def test_select_with_parameter(client: AsyncClient) -> None:
    await client.post("/api/seed")

    response = await client.post(
        "/api/execute-query",
        json={"query": "SELECT * FROM users WHERE username = ?", "parameters": ["alice"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["rows"]) == 1
    assert body["rows"][0]["username"] == "alice"


# ---------------------------------------------------------------------------
# Happy-path INSERT / UPDATE / DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_via_api(client: AsyncClient) -> None:
    response = await client.post(
        "/api/execute-query",
        json={
            "query": "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
            "parameters": ["dave", "dave@example.com", "user"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["rows_affected"] == 1


@pytest.mark.asyncio
async def test_update_via_api(client: AsyncClient) -> None:
    await client.post("/api/seed")

    response = await client.post(
        "/api/execute-query",
        json={
            "query": "UPDATE users SET role = ? WHERE username = ?",
            "parameters": ["superadmin", "alice"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["rows_affected"] == 1


@pytest.mark.asyncio
async def test_delete_via_api(client: AsyncClient) -> None:
    await client.post("/api/seed")

    response = await client.post(
        "/api/execute-query",
        json={
            "query": "DELETE FROM users WHERE username = ?",
            "parameters": ["carol"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["rows_affected"] == 1


# ---------------------------------------------------------------------------
# SQL injection prevention via the API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tautology_injection_returns_no_rows(client: AsyncClient) -> None:
    """Classic  ' OR '1'='1  tautology must not leak all rows."""
    await client.post("/api/seed")

    response = await client.post(
        "/api/execute-query",
        json={
            "query": "SELECT * FROM users WHERE username = ?",
            "parameters": ["' OR '1'='1"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["rows"] == [], "Injection leaked rows — parameterized binding is broken!"


@pytest.mark.asyncio
async def test_union_injection_returns_no_rows(client: AsyncClient) -> None:
    await client.post("/api/seed")

    payload = "alice' UNION SELECT id, username, email, role FROM users --"
    response = await client.post(
        "/api/execute-query",
        json={"query": "SELECT * FROM users WHERE username = ?", "parameters": [payload]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["rows"] == []


# ---------------------------------------------------------------------------
# Disallowed statement types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drop_table_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/execute-query",
        json={"query": "DROP TABLE users", "parameters": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "not permitted" in body["error"]


@pytest.mark.asyncio
async def test_create_table_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/execute-query",
        json={"query": "CREATE TABLE evil (id INTEGER)", "parameters": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False


# ---------------------------------------------------------------------------
# Input validation (Pydantic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_query_field_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/execute-query",
        json={"parameters": ["foo"]},
    )
    assert response.status_code == 422
