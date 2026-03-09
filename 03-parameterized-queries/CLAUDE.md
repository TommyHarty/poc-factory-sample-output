# CLAUDE.md

## Mission header

**POC Index:** 3  
**Title:** Parameterized Queries  
**Slug:** 03-parameterized-queries  

## POC Goal

Demonstrate the use of parameterized queries to prevent SQL injection.

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
- `sqlite3`
- `fastapi`

## Implementation Approach

1. **Core Logic:**  
   The core logic will demonstrate how to use parameterized queries to interact with an SQLite database securely. This involves preparing SQL statements with placeholders for parameters and executing them with actual values to prevent SQL injection.

2. **Modules to Create:**  
   - `app/services/query_service.py`: Contains the logic for executing parameterized queries against the SQLite database.
   - `app/api/routes.py`: Defines the API endpoints for interacting with the database.
   - `app/models/schemas.py`: Defines Pydantic models for request and response validation.

3. **API Surface:**  
   - **Endpoint:** `POST /execute-query`  
     **Input:** JSON object with `query` and `parameters` fields.  
     **Output:** JSON object with the query result or an error message.

4. **OpenAI Usage:**  
   The POC will not directly use OpenAI API calls as the focus is on SQL injection prevention. However, the infrastructure for OpenAI API calls should remain intact for consistency with other POCs.

5. **Tests Must Prove:**  
   - Queries are executed using parameterized statements.
   - SQL injection attempts are thwarted.
   - The API correctly handles valid and invalid input.

## Required file structure

Do NOT pile routes or business logic into `app/main.py`. Use clean separation of concerns:

app/
  main.py              ← thin: only imports router, configures middleware, registers routes
  api/
    routes.py          ← APIRouter with all endpoint handlers
  models/
    schemas.py         ← Pydantic request/response models
  services/
    query_service.py   ← core business logic for this POC
    openai_service.py  ← OpenAI API calls (if the POC uses the model)
tests/
  test_query_service.py ← unit tests for business logic
  test_api.py          ← API-level tests using httpx AsyncClient

`app/main.py` must only:
- Import and include the router from `app/api/routes.py`
- Register middleware if needed
- Expose the `/health` endpoint

All domain logic belongs in `app/services/`. All schemas belong in `app/models/schemas.py`.  
All route handlers belong in `app/api/routes.py` using `APIRouter`.

## Implementation Boundaries

**Include:**
- Demonstration of parameterized queries using SQLite.
- FastAPI endpoints for executing queries.
- Pydantic models for request validation.

**Do NOT Include:**
- ORM usage.
- NoSQL databases.
- Direct OpenAI API calls for this POC.

## Acceptance Criteria

- The application must execute SQL queries using parameterized statements.
- The API must handle SQL injection attempts gracefully.
- The application must be containerized and run successfully using Docker.
- All tests must pass, demonstrating the prevention of SQL injection.

## Testing Requirements

- Use `pytest` for testing.
- Mock database interactions to test parameterized query logic.
- Ensure tests cover both successful query execution and SQL injection prevention.
- Use `httpx.AsyncClient` for API-level tests.

## Repo Hygiene Requirements

- Ensure all code is organized according to the specified file structure.
- Update `pyproject.toml` with any new dependencies.
- Ensure all tests are passing before submission.
- Maintain clean and readable code with appropriate comments.

## Documentation Requirements

- Update `README.md` to explain the POC's purpose, setup, and usage.
- Ensure the README is self-contained and does not reference other POCs or external patterns.
- Include instructions for running the application and tests using Docker.

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