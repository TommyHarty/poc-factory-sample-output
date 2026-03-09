# CLAUDE.md

## Mission Header

This document provides detailed instructions for building a Proof of Concept (POC) focused on implementing output encoding practices to prevent cross-site scripting (XSS) attacks using FastAPI and Pydantic.

## POC Goal

Implement output encoding to prevent cross-site scripting (XSS) attacks.

## Starter Assumptions

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

1. **Core Logic**: Implement output encoding to sanitize user inputs before rendering them in the browser. This involves converting special characters into their HTML-safe equivalents to prevent execution as code.

2. **Modules to Create**:
   - `app/services/encoder.py`: This module will contain the logic for encoding user inputs. It will provide a function to convert special characters into HTML-safe entities.
   - `app/api/routes.py`: Define API endpoints that accept user inputs and return encoded outputs.

3. **API Surface**:
   - Endpoint: `POST /encode`
     - Input: JSON object with a `text` field containing the user input.
     - Output: JSON object with an `encoded_text` field containing the HTML-encoded output.

4. **OpenAI Usage**: This POC does not require OpenAI API calls as it focuses on output encoding practices.

5. **Tests**:
   - Verify that the encoding function correctly converts special characters to HTML entities.
   - Ensure the API endpoint returns the expected encoded output for given inputs.
   - Mock external dependencies as needed, but do not mock the core encoding logic.

## Required File Structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    encoder.py         ← core business logic for this POC
tests/
  test_encoder.py      ← unit tests for business logic
  test_api.py          ← API-level tests using httpx AsyncClient

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.
All route handlers belong in `app/api/routes.py` using `APIRouter`.

## Implementation Boundaries

Include:
- Output encoding logic to prevent XSS.
- API endpoint for encoding user inputs.
- Unit and API tests to validate functionality.

Do NOT include:
- Input validation beyond basic type checks.
- Content security policy implementation.
- Any unrelated business logic or features.

## Acceptance Criteria

- The `/encode` endpoint must accept a JSON payload with a `text` field and return an encoded version of the text.
- Special characters in the input must be converted to their HTML-safe equivalents.
- Tests must cover edge cases, including inputs with no special characters and inputs with multiple special characters.

## Testing Requirements

- Use `pytest` for all tests.
- Mock external dependencies where applicable, but do not mock the encoding logic.
- Ensure tests cover both the encoding function and the API endpoint.

## Repo Hygiene Requirements

- Ensure all code is organized according to the specified file structure.
- Update `pyproject.toml` with any new dependencies.
- Ensure all tests pass and code is linted.
- Maintain clear and concise commit messages.

## Documentation Requirements

- Update `README.md` to include:
  - An overview of the POC and its goal.
  - Instructions for running the application and tests.
  - Examples of API requests and responses.

## Global Implementation Rules

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

## Docker Requirements

The starter repo already has a `Dockerfile` and `docker-compose.yml`. You must work with these existing files, not replace them.

- Always update `docker-compose.yml` to add any infrastructure services the POC needs.
- If the POC requires a service such as ChromaDB, Postgres, Redis, Qdrant, or any other external dependency, add it as a named service in `docker-compose.yml` with the correct image, ports, volumes, and environment variables.
- Add a `depends_on` entry to the app service for any infrastructure services you add.
- Expose the correct ports and set the correct environment variables in `.env.example` so the POC connects to those services.
- Do not remove or replace the existing app service definition — only extend it.
- If no infrastructure services are needed, leave `docker-compose.yml` unchanged.