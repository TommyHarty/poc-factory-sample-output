from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_ipaddr

# Use get_ipaddr so tests can control the rate limit bucket via X-Forwarded-For header.
# In production, this reads the real client IP from X-Forwarded-For or request.client.host.
limiter = Limiter(key_func=get_ipaddr)

# Rate limit for the /login endpoint — 5 attempts per minute per IP.
# This mitigates brute force attacks against the authentication endpoint.
LOGIN_RATE_LIMIT = "5/minute"
