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
