from __future__ import annotations

from app.services.rate_limiter import LOGIN_RATE_LIMIT, limiter


def test_limiter_is_configured() -> None:
    """Limiter instance is created and attached to the module."""
    assert limiter is not None


def test_login_rate_limit_value() -> None:
    """LOGIN_RATE_LIMIT is a non-empty string in the expected format."""
    assert isinstance(LOGIN_RATE_LIMIT, str)
    assert "/" in LOGIN_RATE_LIMIT, "Rate limit must be in 'N/period' format"


def test_login_rate_limit_per_minute() -> None:
    """Rate limit for /login is expressed per minute."""
    assert LOGIN_RATE_LIMIT.endswith("/minute"), (
        "Login should be rate-limited per minute to mitigate brute force"
    )


def test_login_rate_limit_count() -> None:
    """The allowed request count per minute is a positive integer."""
    count_str, _ = LOGIN_RATE_LIMIT.split("/")
    count = int(count_str)
    assert count > 0
