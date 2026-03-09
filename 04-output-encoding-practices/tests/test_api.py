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
