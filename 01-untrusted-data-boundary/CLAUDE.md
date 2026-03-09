# CLAUDE.md

## Mission header

Build a Proof of Concept (POC) to demonstrate the implementation of strict input validation and sanitization at the boundary between user-supplied data and agent instructions using FastAPI and Pydantic.

## POC Goal

Implement a robust system that enforces strict input validation and sanitization to prevent prompt injection attacks, ensuring clear trust boundaries between user input and agent behavior.

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

1. **Core Logic**: Implement a multi-layer defense mechanism that validates and sanitizes user input before it is processed by the OpenAI API. This involves creating a validation service that checks for malicious patterns and a sanitization service that cleans the input data.

2. **Modules to Create**:
   - `app/services/validation_service.py`: Contains logic for input validation, checking for potentially harmful patterns.
   - `app/services/sanitization_service.py`: Contains logic for sanitizing user input to ensure it is safe for processing.
   - `app/services/openai_service.py`: Handles communication with the OpenAI API, using sanitized input.

3. **API Surface**:
   - Endpoint: `POST /process-input`
     - Input: JSON payload with user data to be processed.
     - Output: JSON response with the processed result from the OpenAI API.

4. **OpenAI Usage**: 
   - Structure the prompt to include sanitized user input.
   - Use the OpenAI API to process the input and return a response.
   - The API key is accessed via `settings.openai_api_key.get_secret_value()`.

5. **Tests**:
   - Verify that the validation service correctly identifies and rejects malicious input.
   - Ensure the sanitization service cleans input data as expected.
   - Mock the OpenAI client to test that sanitized input is correctly sent and processed.

## Required file structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    validation_service.py  ← input validation logic
    sanitization_service.py ← input sanitization logic
    openai_service.py  ← OpenAI API calls
tests/
  test_validation_service.py ← unit tests for validation logic
  test_sanitization_service.py ← unit tests for sanitization logic
  test_api.py          ← API-level tests using httpx AsyncClient

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.
All route handlers belong in `app/api/routes.py` using `APIRouter`.

## Implementation Boundaries

Include:
- Input validation and sanitization logic.
- Integration with OpenAI API using sanitized input.
- Unit tests for validation and sanitization services.
- API-level tests for endpoint behavior.

Do NOT include:
- Complex business logic unrelated to input validation.
- Any form of database or persistent storage.
- External services beyond OpenAI.

## Acceptance Criteria

- The system must validate and sanitize all user inputs before processing.
- The `/process-input` endpoint must return a valid response from the OpenAI API using sanitized input.
- Tests must cover all validation and sanitization scenarios, ensuring no malicious input is processed.
- The POC must run successfully in Docker with no errors.

## Testing Requirements

- Use `pytest` for all tests.
- Mock the OpenAI client in tests to avoid real API calls.
- Ensure tests cover both positive and negative scenarios for input validation and sanitization.

## Repo Hygiene Requirements

- Ensure all code is cleanly organized and follows the required file structure.
- Update `pyproject.toml` with any new dependencies.
- Ensure all tests pass before finalizing the POC.

## Documentation Requirements

- Update `README.md` to include clear instructions on running the POC, including setup, execution, and testing.
- Ensure the README is self-contained and does not reference other POCs or external documents.

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