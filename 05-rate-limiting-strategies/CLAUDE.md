# CLAUDE.md

## Mission header

**POC Index:** 5  
**Title:** Rate Limiting Strategies  
**Slug:** 05-rate-limiting-strategies  

## POC Goal

Implement rate limiting to mitigate brute force and denial of service attacks.

## Starter assumptions

This POC starts from an existing FastAPI starter repo that already has Docker configured.

The starter already contains:
- `app/` — the FastAPI application package. `app/main.py` is the entry point.
- `core/` — configuration only. `core/config.py` contains a pydantic-settings `Settings` class that reads from `.env`. It already has `openai_api_key: SecretStr | None`.
- `tests/` — pytest test suite.
- `scripts/` — shell scripts: `setup.sh`, `run.sh`, `test.sh`, `down.sh`.
- `pyproject.toml` — package config and dependencies. Add new packages here. Do NOT create a `requirements.txt`.
- `Dockerfile` and `docker-compose.yml` — already configured.

Do NOT create a `src/` directory. All implementation code goes inside `app/`.  
Do NOT run `pip install -e .` locally — this creates unwanted `.egg-info` artifacts.

## Required Packages

- `slowapi`
- `pydantic`
- `fastapi`

## Implementation Approach

1. **Core Logic**: Implement rate limiting using the `slowapi` package to protect against brute force and denial of service attacks. The rate limiting logic will be applied to specific endpoints, particularly those related to authentication and sensitive operations.

2. **Modules to Create**:
   - `app/services/rate_limiter.py`: This module will contain the logic for configuring and applying rate limits using `slowapi`.
   - `app/api/routes.py`: Define the API routes and apply rate limiting decorators to relevant endpoints.

3. **API Surface**:
   - **Endpoints**:
     - `/login`: POST endpoint for user authentication. Apply rate limiting to prevent brute force attacks.
     - `/health`: GET endpoint for health checks, no rate limiting required.
   - **Inputs/Outputs**:
     - `/login`: Accepts user credentials and returns an authentication token if successful.
     - `/health`: Returns a simple status message.

4. **OpenAI Usage**: This POC does not require direct interaction with the OpenAI API. However, ensure that the `openai_api_key` is correctly configured in `core/config.py` for consistency with other POCs.

5. **Tests**:
   - Verify that rate limiting is correctly applied to the `/login` endpoint.
   - Ensure that requests exceeding the rate limit receive the appropriate HTTP status code (e.g., 429 Too Many Requests).
   - Mock infrastructure side effects as needed, but do not mock the core rate limiting logic.

## Required file structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

```
app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    rate_limiter.py    ← core business logic for this POC
tests/
  test_rate_limiter.py ← unit tests for business logic
  test_api.py          ← API-level tests using httpx AsyncClient
```

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.  
All route handlers belong in `app/api/routes.py` using `APIRouter`.

## Implementation Boundaries

- **Include**:
  - Rate limiting logic using `slowapi`.
  - Authentication endpoint with rate limiting.
  - Unit and API tests to verify rate limiting behavior.

- **Do NOT Include**:
  - IP blacklisting logic.
  - Any unrelated OpenAI API calls.
  - Additional authentication mechanisms beyond basic rate limiting.

## Acceptance Criteria

- The `/login` endpoint must have rate limiting applied.
- Requests exceeding the rate limit must receive a 429 status code.
- The `/health` endpoint must remain accessible without rate limiting.
- All tests must pass, demonstrating correct rate limiting behavior.

## Testing Requirements

- Use `pytest` for all tests.
- Mock infrastructure side effects where appropriate, but do not mock the rate limiting logic.
- Use `httpx.AsyncClient` with `ASGITransport` for API tests.
- Verify that rate limits are enforced and that appropriate responses are returned.

## Repo Hygiene Requirements

- Ensure all code is organized according to the required file structure.
- Update `pyproject.toml` with any new dependencies.
- Maintain clean and readable code with appropriate comments and documentation.

## Documentation Requirements

- Update `README.md` to provide a clear overview of the POC, including setup instructions, how to run the application, and how to test it.
- Ensure the README is self-contained and does not reference other POCs or external resources.

## Global implementation rules

- Use Python.
- Use FastAPI for the API surface. All routes go in `app/api/routes.py` via `APIRouter`. `app/main.py` only wires things together.
- Keep the POC lightweight and focused on one concept.
- **Use the real OpenAI API for all LLM calls.** Do NOT simulate or stub model responses. The starter repo's `core/config.py` already exposes `settings.openai_api_key` (a `SecretStr`). Access it with `settings.openai_api_key.get_secret_value()`. Isolate all OpenAI calls in `app/services/openai_service.py`.
- Mock only infrastructure side effects that are genuinely external and irrelevant to the concept being demonstrated (e.g. email sending, browser automation, secret manager calls). Do NOT mock OpenAI.
- Organize the code cleanly into `app/models/`, `app/services/`, `app/api/`.
- Add tests in `tests/`. Use `httpx.AsyncClient` with `ASGITransport` for API tests. Mock the OpenAI client in tests using `unittest.mock.patch` or `pytest-mock` so tests do not make real API calls.
- Ensure imports and typing are correct. Use `from __future__ import annotations`.
- Update `README.md` so the POC is easy to understand and run.
- Update `.env.example` with any new environment variables. `OPENAI_API_KEY` is already present.
- Add new packages to `pyproject.toml` under `[project] dependencies`. Do NOT create or modify a `requirements.txt`.

## Docker requirements

The starter repo already has a `Dockerfile` and `docker-compose.yml`. You must work with these existing files, not replace them.

- Always update `docker-compose.yml` to add any infrastructure services the POC needs.
- If the POC requires a service such as ChromaDB, Postgres, Redis, Qdrant, or any other external dependency, add it as a named service in `docker-compose.yml` with the correct image, ports, volumes, and environment variables.
- Add a `depends_on` entry to the app service for any infrastructure services you add.
- Expose the correct ports and set the correct environment variables in `.env.example` so the POC connects to those services.
- Do not remove or replace the existing app service definition — only extend it.
- If no infrastructure services are needed, leave `docker-compose.yml` unchanged.