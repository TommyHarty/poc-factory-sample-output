# CLAUDE.md

## Mission header

Build a Proof of Concept (POC) for input schema enforcement using Pydantic models in a FastAPI application to ensure strict input validation for all API endpoints.

## POC Goal

Use Pydantic models to enforce strict input schemas for all API endpoints, ensuring that only well-formed data reaches the application logic, thereby reducing injection risks.

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

- `pydantic`
- `fastapi`

## Implementation Approach

1. **Core Logic**: Implement input validation using Pydantic models to define strict schemas for all incoming API requests. This ensures that only valid data is processed by the application logic, reducing the risk of injection attacks.

2. **Modules to Create**:
   - `app/models/schemas.py`: Define Pydantic models for request and response schemas.
   - `app/api/routes.py`: Implement API endpoints using FastAPI's `APIRouter`. Each endpoint should validate incoming requests against the defined Pydantic models.
   - `app/services/validator.py`: Implement any additional validation logic if needed, though primary validation should occur through Pydantic models.

3. **API Surface**:
   - Endpoint: `/submit-data`
     - Method: POST
     - Input: JSON object validated against a Pydantic model
     - Output: Success or error message based on validation

4. **OpenAI Usage**: This POC does not require direct OpenAI API calls as its focus is on input validation using Pydantic models.

5. **Tests**:
   - Ensure that invalid inputs are rejected with appropriate error messages.
   - Verify that valid inputs are accepted and processed correctly.
   - Mock external dependencies where necessary, but do not mock the core validation logic.

## Required file structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    validator.py       ← core business logic for this POC
tests/
  test_validator.py    ← unit tests for business logic
  test_api.py          ← API-level tests using httpx AsyncClient

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.
All route handlers belong in `app/api/routes.py` using `APIRouter`.

## Implementation Boundaries

- **Include**: Input validation using Pydantic models, API endpoint implementation, and comprehensive testing.
- **Do NOT Include**: Output validation, runtime type checking beyond Pydantic's capabilities, or unrelated business logic.

## Acceptance Criteria

- All API endpoints must validate inputs against defined Pydantic models.
- Invalid inputs must result in a 400 error with a descriptive message.
- Valid inputs must be processed without errors.
- Tests must cover both valid and invalid input scenarios.

## Testing Requirements

- Use `pytest` for all tests.
- Mock external dependencies where necessary, but do not mock the core validation logic.
- Use `httpx.AsyncClient` for API-level tests to simulate client requests.

## Repo Hygiene Requirements

- Ensure all code is organized according to the required file structure.
- Update `pyproject.toml` with any new dependencies.
- Ensure all imports and typing are correct.
- Maintain clean and readable code with appropriate comments.

## Documentation Requirements

- Update `README.md` to include clear instructions on setting up and running the POC.
- Ensure the README is self-contained and does not reference other POCs or external patterns.

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