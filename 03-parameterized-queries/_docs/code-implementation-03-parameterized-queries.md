# Code Implementation: Parameterized Queries

## Overview

In this guide, we will walk through the implementation of a Proof of Concept (POC) that demonstrates the use of parameterized queries to prevent SQL injection attacks. By the end of this guide, you will have a working FastAPI application that securely executes SQL queries against an SQLite database using parameterized queries.

## Prerequisites

- Python 3.11 or higher
- Key packages: FastAPI, Pydantic, SQLite3
- No external services are required; the SQLite database is used in-memory.

## Implementation Steps

### Step 1: Define Data Models and Schemas

**File**: `app/models/schemas.py`

This file defines the data models used for request and response validation in the API. We use Pydantic to create models that validate incoming data for executing SQL queries and seeding the database. The models ensure that queries are parameterized, which helps in preventing SQL injection.

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecuteQueryRequest(BaseModel):
    """Request model for the parameterized query endpoint.

    The caller supplies a SQL template with ? placeholders and a list of
    positional parameter values. The service substitutes the values safely
    via the DB driver — never via string interpolation.
    """

    query: str = Field(
        ...,
        description="SQL query with ? placeholders for parameters.",
        examples=["SELECT * FROM users WHERE username = ?"],
    )
    parameters: list[Any] = Field(
        default_factory=list,
        description="Positional parameter values that map to each ? placeholder.",
        examples=[["alice"]],
    )


class ExecuteQueryResponse(BaseModel):
    """Response model returned after executing a parameterized query."""

    success: bool
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Rows returned by the query (empty for non-SELECT statements).",
    )
    rows_affected: int = Field(
        default=0,
        description="Number of rows affected (INSERT / UPDATE / DELETE).",
    )
    error: str | None = Field(
        default=None,
        description="Error message when success is False.",
    )


class SeedResponse(BaseModel):
    """Response returned by the seed endpoint."""

    message: str
    rows_inserted: int
```

### Step 2: Implement the Query Service

**File**: `app/services/query_service.py`

This file contains the core logic for executing parameterized SQL queries. The `QueryService` class manages the SQLite database connection and provides methods to execute queries and seed the database with demo data. It ensures that all queries use parameterized placeholders to prevent SQL injection.

```python
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator

# Allowlist of permitted SQL statement prefixes.
# This restricts the surface area available through the demo endpoint so the
# POC cannot be misused to execute arbitrary DDL or admin statements.
ALLOWED_PREFIXES: frozenset[str] = frozenset({"SELECT", "INSERT", "UPDATE", "DELETE"})


class QueryError(Exception):
    """Raised when a query cannot be executed safely."""


class QueryService:
    """Executes SQL statements against an in-process SQLite database using
    parameterized queries to prevent SQL injection.

    The database is created in memory by default, which makes the service
    self-contained and easy to test without any filesystem side effects.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        # Use check_same_thread=False because FastAPI may dispatch requests
        # across threads.  For a demo/POC an in-memory DB is sufficient.
        self._conn: sqlite3.Connection = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self._bootstrap()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(
        self, query: str, parameters: list[Any]
    ) -> tuple[list[dict[str, Any]], int]:
        """Execute *query* with *parameters* using the DB driver's parameterized
        binding — never via string formatting.

        Returns a tuple of:
          - rows: list of dicts (non-empty for SELECT statements)
          - rows_affected: number of rows changed (INSERT / UPDATE / DELETE)

        Raises QueryError for disallowed or malformed statements.
        """
        self._validate_statement(query)

        try:
            cursor = self._conn.execute(query, parameters)
            self._conn.commit()
        except sqlite3.Error as exc:
            # Roll back any partial changes so the DB stays consistent.
            self._conn.rollback()
            raise QueryError(str(exc)) from exc

        rows: list[dict[str, Any]] = [dict(row) for row in cursor.fetchall()]
        rows_affected: int = cursor.rowcount if cursor.rowcount >= 0 else 0
        return rows, rows_affected

    def seed_demo_data(self) -> int:
        """Insert a small set of demo users so the API has data to query.

        Returns the number of rows inserted.
        """
        users = [
            ("alice", "alice@example.com", "admin"),
            ("bob", "bob@example.com", "user"),
            ("carol", "carol@example.com", "user"),
        ]
        # Use executemany with parameterized placeholders — still safe.
        self._conn.executemany(
            "INSERT OR IGNORE INTO users (username, email, role) VALUES (?, ?, ?)",
            users,
        )
        self._conn.commit()
        return len(users)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _bootstrap(self) -> None:
        """Create the demo schema on first use."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                email    TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'user'
            )
            """
        )
        self._conn.commit()

    def _validate_statement(self, query: str) -> None:
        """Reject statements whose first token is not in the allowlist.

        This is a defence-in-depth measure on top of parameterized binding.
        It prevents callers from executing DDL (DROP TABLE, ALTER TABLE …)
        or multi-statement injections through the demo endpoint.
        """
        first_token = query.strip().split()[0].upper() if query.strip() else ""
        if first_token not in ALLOWED_PREFIXES:
            raise QueryError(
                f"Statement type '{first_token}' is not permitted. "
                f"Allowed: {sorted(ALLOWED_PREFIXES)}"
            )


# Module-level singleton — created once when the module is first imported.
# Tests can override this by patching or by constructing their own instance.
_default_service: QueryService | None = None


def get_query_service() -> QueryService:
    """Return the module-level QueryService singleton."""
    global _default_service
    if _default_service is None:
        _default_service = QueryService()
    return _default_service
```

### Step 3: Define API Routes

**File**: `app/api/routes.py`

This file defines the API endpoints for executing SQL queries and seeding the database. The `/execute-query` endpoint accepts a SQL query with parameter placeholders and executes it using the `QueryService`. The `/seed` endpoint populates the database with initial data.

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import ExecuteQueryRequest, ExecuteQueryResponse, SeedResponse
from app.services.query_service import QueryError, QueryService, get_query_service

router = APIRouter(prefix="/api", tags=["queries"])


@router.post(
    "/execute-query",
    response_model=ExecuteQueryResponse,
    summary="Execute a parameterized SQL query",
    description=(
        "Accepts a SQL statement with ? placeholders and a list of positional "
        "parameter values. The values are bound by the SQLite driver — never via "
        "string interpolation — so SQL injection is structurally impossible."
    ),
)
def execute_query(
    body: ExecuteQueryRequest,
    service: QueryService = Depends(get_query_service),
) -> ExecuteQueryResponse:
    try:
        rows, rows_affected = service.execute(body.query, body.parameters)
        return ExecuteQueryResponse(
            success=True,
            rows=rows,
            rows_affected=rows_affected,
        )
    except QueryError as exc:
        # Return a structured error response rather than a 500.
        # The caller can inspect `success=False` and read the `error` field.
        return ExecuteQueryResponse(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/seed",
    response_model=SeedResponse,
    summary="Seed the demo database with sample users",
    description="Inserts a small set of demo rows so /execute-query has data to return.",
)
def seed(
    service: QueryService = Depends(get_query_service),
) -> SeedResponse:
    rows_inserted = service.seed_demo_data()
    return SeedResponse(
        message="Demo data seeded successfully.",
        rows_inserted=rows_inserted,
    )
```

### Step 4: Set Up the Main Application

**File**: `app/main.py`

This file initializes the FastAPI application and includes the API routes. It also provides a basic health check endpoint to verify that the application is running.

```python
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="POC: Parameterized Queries — preventing SQL injection at the driver level.",
)

app.include_router(router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
    }
```

### Step 5: Write Tests for the API

**File**: `tests/test_api.py`

This file contains tests for the API endpoints. It uses `pytest` and `httpx` to test the `/execute-query` and `/seed` endpoints, ensuring that they function correctly and are resistant to SQL injection attacks.

```python
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
```

### Step 6: Define Project Dependencies

**File**: `pyproject.toml`

This file specifies the project's dependencies, including FastAPI, Pydantic, and testing tools like pytest. It ensures that all necessary packages are installed for the application to run and be tested.

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
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "anyio[trio]",
    "httpx",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "core*"]
```

## Verification

To confirm that the POC is working:

1. Run the application using the command: `./scripts/run.sh`
2. Execute the tests to ensure everything is functioning correctly: `./scripts/test.sh`
3. Test the `/api/execute-query` and `/api/seed` endpoints using a tool like Postman or curl. You should see successful responses and no SQL injection vulnerabilities.

## Key Takeaway

The most important insight from this POC is the use of parameterized queries to prevent SQL injection attacks. By using parameterized placeholders and a strict allowlist of SQL operations, the application ensures that user input cannot be used to execute malicious SQL commands. This approach provides a robust defense against one of the most common security vulnerabilities in web applications.