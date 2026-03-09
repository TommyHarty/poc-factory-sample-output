# Code Implementation: Output Encoding Practices

## Overview

In this guide, we will implement a proof-of-concept (POC) application that demonstrates output encoding practices to prevent cross-site scripting (XSS) attacks. By the end of this guide, you will have a working FastAPI application that encodes user input to HTML-safe text, ensuring that any special characters are safely rendered in a browser context.

## Prerequisites

- Python 3.11 or higher
- Key packages: `fastapi`, `pydantic`, `uvicorn`
- Optional for development: `pytest`, `httpx`

## Implementation Steps

## Step 1: Define Request and Response Schemas

**File**: `app/models/schemas.py`

This file defines the data models for the API using Pydantic. We have two models: `EncodeRequest` for incoming data and `EncodeResponse` for outgoing data. These models ensure that the data structure is validated and serialized correctly.

```python
from __future__ import annotations

from pydantic import BaseModel


class EncodeRequest(BaseModel):
    text: str


class EncodeResponse(BaseModel):
    encoded_text: str
```

## Step 2: Implement the HTML Encoder Service

**File**: `app/services/encoder.py`

This file contains the core business logic for encoding text. The `html_encode` function converts special characters to their HTML-safe equivalents, preventing XSS by ensuring user-supplied strings cannot be interpreted as HTML or JavaScript.

```python
from __future__ import annotations

import html


def html_encode(text: str) -> str:
    """Convert special characters to their HTML-safe equivalents.

    This prevents XSS by ensuring user-supplied strings cannot be interpreted
    as HTML or JavaScript when rendered in a browser context.

    Characters encoded: &, <, >, ", '
    """
    return html.escape(text, quote=True)
```

## Step 3: Set Up API Routes

**File**: `app/api/routes.py`

This file sets up the FastAPI routes. It includes a POST endpoint `/encode` that accepts raw user text and returns its HTML-encoded equivalent. This demonstrates output encoding as a defense against XSS attacks.

```python
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import EncodeRequest, EncodeResponse
from app.services.encoder import html_encode

router = APIRouter()


@router.post("/encode", response_model=EncodeResponse)
def encode_text(payload: EncodeRequest) -> EncodeResponse:
    """Accept raw user text and return its HTML-encoded equivalent.

    This endpoint demonstrates output encoding as a defence against XSS:
    any special characters in the input are converted to HTML entities
    before the value is returned to the caller for use in rendered output.
    """
    return EncodeResponse(encoded_text=html_encode(payload.text))
```

## Step 4: Configure the FastAPI Application

**File**: `app/main.py`

This file initializes the FastAPI application and includes the router defined in the previous step. It also sets up a basic health check endpoint to ensure the application is running correctly.

```python
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
    }
```

## Step 5: Write Tests for the API

**File**: `tests/test_api.py`

This file contains tests for the API endpoints using `httpx` and `pytest`. The tests ensure that the `/encode` endpoint correctly encodes input text and handles various edge cases, such as missing fields and special characters.

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_encode_plain_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/encode", json={"text": "hello world"})
    assert response.status_code == 200
    assert response.json()["encoded_text"] == "hello world"


@pytest.mark.anyio
async def test_encode_xss_script_tag():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/encode", json={"text": '<script>alert("XSS")</script>'})
    assert response.status_code == 200
    body = response.json()
    assert "<script>" not in body["encoded_text"]
    assert "&lt;script&gt;" in body["encoded_text"]


@pytest.mark.anyio
async def test_encode_ampersand():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/encode", json={"text": "rock & roll"})
    assert response.status_code == 200
    assert response.json()["encoded_text"] == "rock &amp; roll"


@pytest.mark.anyio
async def test_encode_empty_string():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/encode", json={"text": ""})
    assert response.status_code == 200
    assert response.json()["encoded_text"] == ""


@pytest.mark.anyio
async def test_encode_missing_field_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/encode", json={})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_health_still_works():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Step 6: Write Tests for the Encoder Service

**File**: `tests/test_encoder.py`

This file contains unit tests for the `html_encode` function. It tests various scenarios to ensure that special characters are correctly encoded and that the function handles edge cases like empty strings and already safe text.

```python
from __future__ import annotations

import pytest

from app.services.encoder import html_encode


def test_no_special_characters():
    assert html_encode("hello world") == "hello world"


def test_ampersand():
    assert html_encode("rock & roll") == "rock &amp; roll"


def test_less_than():
    assert html_encode("<script>") == "&lt;script&gt;"


def test_greater_than():
    assert html_encode("x > y") == "x &gt; y"


def test_double_quote():
    assert html_encode('say "hello"') == "say &quot;hello&quot;"


def test_single_quote():
    assert html_encode("it's fine") == "it&#x27;s fine"


def test_full_xss_payload():
    raw = '<script>alert("XSS")</script>'
    encoded = html_encode(raw)
    assert "<script>" not in encoded
    assert "&lt;script&gt;" in encoded
    assert "&quot;" in encoded


def test_multiple_special_characters():
    raw = "<b>Hello & 'World'</b>"
    encoded = html_encode(raw)
    assert "&lt;" in encoded
    assert "&gt;" in encoded
    assert "&amp;" in encoded
    assert "&#x27;" in encoded


def test_empty_string():
    assert html_encode("") == ""


def test_already_safe_text():
    safe = "Just a plain sentence without special chars."
    assert html_encode(safe) == safe
```

## Step 7: Test the Health Check Endpoint

**File**: `tests/test_health.py`

This file tests the `/health` endpoint to ensure that the application is running and returns the expected status and configuration details.

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

## Step 8: Define Project Dependencies

**File**: `pyproject.toml`

This file specifies the project's dependencies and build configuration. It includes essential packages for running the FastAPI application and optional packages for development and testing.

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
    "pytest-anyio",
    "anyio[trio]",
    "httpx",
]

[tool.pytest.ini_options]
anyio_mode = "auto"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "core*"]
```

## Verification

To confirm the POC is working:

1. Run the application using the command: `./scripts/run.sh`
2. Execute the tests to ensure everything is functioning correctly: `./scripts/test.sh`
3. Test the `/encode` endpoint by sending a POST request with JSON data containing a `text` field. Verify that the response contains the HTML-encoded text.

## Key Takeaway

The most important insight from this POC is the implementation of output encoding as a defense against XSS attacks. By converting special characters to their HTML-safe equivalents, we can ensure that user input is safely rendered in a browser context, preventing malicious scripts from executing.