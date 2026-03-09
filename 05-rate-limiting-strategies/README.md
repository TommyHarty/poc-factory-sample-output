# 05 — Rate Limiting Strategies

**POC:** `05-rate-limiting-strategies`
**Topic:** Prompt Injection Guardrails

## What it demonstrates

This POC shows how to apply per-IP rate limiting to sensitive endpoints (e.g. `/login`) using [`slowapi`](https://github.com/laurentS/slowapi) — a thin wrapper around the [`limits`](https://github.com/alisaifee/limits) library built for FastAPI and Starlette.

When a client exceeds the configured threshold the server returns **HTTP 429 Too Many Requests**, preventing brute force and denial-of-service attacks on authentication endpoints.

## Why it matters

Login endpoints are the most common target for credential-stuffing and brute-force attacks. Without rate limiting, an attacker can make unlimited password guesses. A simple per-IP rate limit raises the cost of an attack dramatically with minimal application complexity.

## Architecture overview

```
app/
  main.py              ← Registers limiter, middleware, exception handler, and router
  api/
    routes.py          ← POST /login with @limiter.limit() decorator
  models/
    schemas.py         ← LoginRequest / LoginResponse Pydantic models
  services/
    rate_limiter.py    ← Limiter instance and LOGIN_RATE_LIMIT constant
core/
  config.py            ← Pydantic Settings (app name, env, port, OpenAI key)
tests/
  conftest.py          ← Shared AsyncClient fixture
  test_rate_limiter.py ← Unit tests for rate limiter configuration
  test_api.py          ← API-level tests for /login and /health
```

### How slowapi works

1. A `Limiter` instance is created with a `key_func` that extracts the client identifier (IP address).
2. `app.state.limiter = limiter` makes the limiter available to the middleware.
3. `SlowAPIMiddleware` intercepts every request and checks the current usage against the limit for the decorated endpoint.
4. `_rate_limit_exceeded_handler` translates `RateLimitExceeded` exceptions into 429 responses.
5. Each route is decorated with `@limiter.limit("5/minute")` to apply the constraint.

## Project structure

```
.
├── app/
│   ├── api/routes.py
│   ├── models/schemas.py
│   ├── services/rate_limiter.py
│   └── main.py
├── core/config.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_rate_limiter.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Getting started

```bash
cp .env.example .env
./scripts/setup.sh
```

## Running

```bash
./scripts/run.sh
# or
docker compose up
```

The app is available at `http://localhost:8000`.

## Endpoints

### `GET /health`

Returns service status. No rate limiting applied.

```json
{"status": "ok", "app_name": "Rate Limiting POC", "app_env": "local"}
```

### `POST /login`

Rate-limited to **5 requests per minute per IP**.

Request:
```json
{"username": "alice", "password": "secret"}
```

Success (200):
```json
{"access_token": "demo-token", "token_type": "bearer"}
```

Rate limit exceeded (429):
```json
{"error": "Rate limit exceeded: 5 per 1 minute"}
```

## Testing

```bash
./scripts/test.sh
# or
docker compose run --rm app pytest tests/ -v
```

All tests are async (`pytest-asyncio`) and use `httpx.AsyncClient` with `ASGITransport` — no real server is started. Each test uses a distinct `X-Forwarded-For` IP to isolate rate limit buckets between tests.

## Environment variables

| Variable        | Default               | Notes                          |
|-----------------|-----------------------|--------------------------------|
| `APP_NAME`      | `Rate Limiting POC`   |                                |
| `APP_ENV`       | `local`               |                                |
| `API_HOST`      | `0.0.0.0`             |                                |
| `API_PORT`      | `8000`                |                                |
| `OPENAI_API_KEY`| _(empty)_             | Not used by this POC           |

## Key limitations

- Rate limit state is stored **in-memory**. It resets on app restart and is not shared across multiple instances (no Redis backend).
- The `LOGIN_RATE_LIMIT` constant (`5/minute`) is hardcoded for simplicity. A production system should make this configurable via environment variable.
- The `/login` endpoint does not validate credentials — the POC focuses on demonstrating rate limiting, not authentication.

## Next logical POCs

- **06 — Input Sanitization** — validate and sanitize user input before processing
- **07 — Output Schema Validation** — enforce structured output from LLMs to prevent prompt injection via malformed responses
- **Redis-backed rate limiting** — share rate limit state across multiple app instances using `limits` with a Redis storage backend
