from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Untrusted Data Boundary POC",
    description=(
        "Demonstrates strict input validation and sanitization as a "
        "trust-boundary guardrail against prompt injection."
    ),
    version="0.1.0",
)

app.include_router(router)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_env": settings.app_env,
    }
