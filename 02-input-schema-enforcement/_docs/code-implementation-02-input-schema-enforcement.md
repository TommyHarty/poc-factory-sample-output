# Code Implementation: Input Schema Enforcement

## Overview

In this guide, we will build a proof-of-concept (POC) application using FastAPI and Pydantic to enforce strict input schemas for API endpoints. By the end of this guide, you will have a working application that validates incoming data against defined schemas, ensuring data integrity and security through schema enforcement and additional semantic validation.

## Prerequisites

- Python 3.11 or higher
- Key packages: FastAPI, Pydantic, Uvicorn
- Optional for development: Pytest, HTTPX

## Implementation Steps

### Step 1: Define Data Schemas

**File**: `app/models/schemas.py`

This file defines the data models using Pydantic. The `DataSubmission` model enforces strict schema rules, such as allowed fields and value constraints, while the `SubmissionResponse` model defines the structure of the response returned by the API.

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataSubmission(BaseModel):
    """Strictly typed request body for /submit-data.

    ``extra="forbid"`` rejects any unrecognised fields, closing a common
    vector where attackers sneak additional keys into a JSON payload hoping
    the application processes them without validation.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Alphanumeric user identifier — no spaces or special chars",
    )
    action: Literal["read", "write", "delete"] = Field(
        ...,
        description="Whitelisted action type — only these three values are accepted",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Payload content; bounded to prevent oversized input attacks",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Optional list of lowercase tags",
    )


class SubmissionResponse(BaseModel):
    """Response model for a successful data submission."""

    status: str
    message: str
    validated_action: str
    user_id: str
```

### Step 2: Implement Semantic Validation

**File**: `app/services/validator.py`

This file contains additional validation logic that checks for semantic issues such as injection patterns in the content and validates the format of tags. This goes beyond Pydantic's structural validation.

```python
from __future__ import annotations

import re

from app.models.schemas import DataSubmission

# Content-level patterns that indicate likely injection attempts.
# Pydantic handles structural enforcement (types, lengths, enums, extra fields).
# This layer catches semantic signals that structural types cannot express.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    # SQL terminators / comment sequences
    re.compile(r"(--|;|/\*|\*/)", re.IGNORECASE),
    # Common SQL DML/DDL keywords used in injection payloads
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|EXEC)\b", re.IGNORECASE),
]

# Tags must be lowercase alphanumeric with hyphens/underscores, max 32 chars.
_TAG_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def contains_injection_patterns(value: str) -> bool:
    """Return True if *value* matches any known injection pattern."""
    return any(pattern.search(value) for pattern in _INJECTION_PATTERNS)


def validate_submission(submission: DataSubmission) -> tuple[bool, str | None]:
    """Perform semantic validation on top of Pydantic's structural checks.

    Returns ``(True, None)`` when the submission is clean, or
    ``(False, reason)`` when a semantic violation is detected.

    Pydantic already enforces field types, lengths, regex patterns for
    ``user_id``, the ``action`` allowlist, and the ``extra="forbid"``
    policy.  This function adds one more layer: content-level injection
    signal detection and tag format enforcement.
    """
    if contains_injection_patterns(submission.content):
        return False, "Content contains disallowed patterns"

    if submission.tags:
        for tag in submission.tags:
            if not _TAG_PATTERN.match(tag):
                return (
                    False,
                    f"Tag '{tag}' must be lowercase alphanumeric (hyphens/underscores "
                    "allowed) and at most 32 characters",
                )

    return True, None
```

### Step 3: Define API Routes

**File**: `app/api/routes.py`

This file sets up the API endpoint `/submit-data` using FastAPI. It uses the `DataSubmission` schema to enforce input validation and calls the `validate_submission` function for additional checks.

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import DataSubmission, SubmissionResponse
from app.services.validator import validate_submission

router = APIRouter()


@router.post("/submit-data", response_model=SubmissionResponse)
async def submit_data(body: DataSubmission) -> SubmissionResponse:
    """Accept a strictly-typed data submission.

    FastAPI + Pydantic enforce structural constraints automatically:
    - Unknown fields are rejected (``extra="forbid"``).
    - ``user_id`` must match ``^[a-zA-Z0-9_-]+$``.
    - ``action`` must be one of ``read | write | delete``.
    - ``content`` is bounded to 1–500 characters.

    The validator service then applies semantic checks (injection patterns,
    tag format) that structural types cannot express.

    Returns 422 for schema violations (FastAPI default).
    Returns 400 for semantic violations detected by the validator.
    """
    is_valid, error_msg = validate_submission(body)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    return SubmissionResponse(
        status="accepted",
        message="Data passed schema enforcement checks",
        validated_action=body.action,
        user_id=body.user_id,
    )
```

### Step 4: Set Up the FastAPI Application

**File**: `app/main.py`

This file initializes the FastAPI application and includes the API router defined in `routes.py`. It sets up the application with a title from the configuration.

```python
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(router)
```

### Step 5: Write Tests for API and Validation

**File**: `tests/test_api.py`

This file contains tests for the API endpoints, ensuring that the input validation works as expected. It tests both valid and invalid scenarios.

```python
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
```

**File**: `tests/test_validator.py`

This file contains unit tests for the validation logic, ensuring that the semantic checks work correctly.

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import DataSubmission
from app.services.validator import contains_injection_patterns, validate_submission


def _valid() -> DataSubmission:
    return DataSubmission(user_id="user_42", action="read", content="Fetch profile data")


# ---------------------------------------------------------------------------
# contains_injection_patterns
# ---------------------------------------------------------------------------


class TestContainsInjectionPatterns:
    def test_clean_string_passes(self) -> None:
        assert not contains_injection_patterns("hello world")

    def test_sql_select_detected(self) -> None:
        assert contains_injection_patterns("SELECT * FROM users")

    def test_sql_drop_detected(self) -> None:
        assert contains_injection_patterns("DROP TABLE sessions")

    def test_sql_comment_detected(self) -> None:
        assert contains_injection_patterns("valid -- DROP TABLE users")

    def test_sql_union_detected(self) -> None:
        assert contains_injection_patterns("1 UNION SELECT password FROM users")

    def test_script_tag_detected(self) -> None:
        assert contains_injection_patterns("<script>alert(1)</script>")

    def test_javascript_uri_detected(self) -> None:
        assert contains_injection_patterns("javascript:void(0)")

    def test_mixed_case_sql_detected(self) -> None:
        assert contains_injection_patterns("sElEcT 1")


# ---------------------------------------------------------------------------
# validate_submission — semantic layer
# ---------------------------------------------------------------------------


class TestValidateSubmission:
    def test_valid_submission(self) -> None:
        ok, err = validate_submission(_valid())
        assert ok is True
        assert err is None

    def test_sql_in_content_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="write", content="DROP TABLE users")
        ok, err = validate_submission(s)
        assert ok is False
        assert err is not None

    def test_script_in_content_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="write", content="<script>xss</script>")
        ok, err = validate_submission(s)
        assert ok is False

    def test_invalid_tag_chars_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["UPPERCASE"])
        ok, err = validate_submission(s)
        assert ok is False
        assert err is not None

    def test_tag_with_spaces_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["bad tag"])
        ok, err = validate_submission(s)
        assert ok is False

    def test_tag_too_long_rejected(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["a" * 33])
        ok, err = validate_submission(s)
        assert ok is False

    def test_valid_tags_accepted(self) -> None:
        s = DataSubmission(user_id="u1", action="read", content="ok", tags=["tag-1", "tag_2"])
        ok, err = validate_submission(s)
        assert ok is True

    def test_no_tags_is_valid(self) -> None:
        ok, err = validate_submission(_valid())
        assert ok is True


# ---------------------------------------------------------------------------
# DataSubmission schema — Pydantic structural enforcement
# ---------------------------------------------------------------------------


class TestDataSubmissionSchema:
    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="ok", extra_field="bad")  # type: ignore[call-arg]

    def test_user_id_with_spaces_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="bad user", action="read", content="ok")

    def test_user_id_with_special_chars_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1!", action="read", content="ok")

    def test_user_id_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="a" * 65, action="read", content="ok")

    def test_unknown_action_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="execute", content="ok")  # type: ignore[arg-type]

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="")

    def test_oversized_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DataSubmission(user_id="u1", action="read", content="x" * 501)

    def test_valid_submission_accepted(self) -> None:
        s = _valid()
        assert s.user_id == "user_42"
        assert s.action == "read"

    def test_all_valid_actions_accepted(self) -> None:
        for action in ("read", "write", "delete"):
            s = DataSubmission(user_id="u1", action=action, content="ok")  # type: ignore[arg-type]
            assert s.action == action
```

### Step 6: Configure Project Dependencies

**File**: `pyproject.toml`

This file specifies the project dependencies, including FastAPI, Pydantic, and Uvicorn for running the application, as well as testing dependencies.

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
    "httpx",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "core*"]
```

## Verification

To confirm the POC is working:

- Run the application using the command: `./scripts/run.sh`
- Execute the tests to ensure everything is functioning correctly: `./scripts/test.sh`
- Test the `/submit-data` endpoint by sending valid and invalid requests to verify schema enforcement and validation.

## Key Takeaway

The most important insight from this POC is the power of combining FastAPI with Pydantic to enforce strict input validation through schemas. This approach not only ensures data integrity but also provides a robust defense against common injection attacks by layering semantic validation on top of structural checks.