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
