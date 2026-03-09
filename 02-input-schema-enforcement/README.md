# 02 — Input Schema Enforcement

Demonstrates how Pydantic models enforce **strict input schemas** at every API boundary, reducing injection risk before application logic ever runs.

## What it demonstrates

- `extra="forbid"` on Pydantic models — unknown fields are rejected outright
- Field-level constraints: type coercion, `min_length`/`max_length`, `pattern` regex
- Enum-style enforcement via `Literal` — only whitelisted values are accepted
- A second semantic validation layer that catches content-level injection signals (SQL keywords, `<script>` tags) that structural types cannot express
- Clean separation between schema definition (`app/models/`), validation logic (`app/services/`), and route handlers (`app/api/`)

## Why it matters

Schema enforcement is a foundational guardrail. Without it, arbitrary payloads reach application code and downstream systems. Pydantic's validation runs synchronously, before any handler logic, so malformed or adversarial inputs are rejected at the boundary with a structured 422 response. The semantic layer adds defence-in-depth against content that is structurally valid but semantically dangerous.

## Architecture

```
POST /submit-data
      │
      ▼
FastAPI deserialization
      │
      ▼
Pydantic DataSubmission model          ← structural enforcement
  • extra="forbid" (unknown fields)
  • user_id: pattern ^[a-zA-Z0-9_-]+$
  • action: Literal["read","write","delete"]
  • content: 1–500 chars
      │
      ▼
validator.validate_submission()        ← semantic enforcement
  • injection pattern scan on content
  • tag format check
      │
      ▼
SubmissionResponse (200) or HTTPException (400/422)
```

## Project structure

```
.
├── app/
│   ├── main.py              # thin: wires router, /health
│   ├── api/
│   │   └── routes.py        # APIRouter — /submit-data handler
│   ├── models/
│   │   └── schemas.py       # DataSubmission, SubmissionResponse
│   └── services/
│       └── validator.py     # semantic validation logic
├── core/
│   └── config.py            # pydantic-settings Settings
├── tests/
│   ├── test_validator.py    # unit tests for schemas and validator
│   └── test_api.py          # API-level tests via httpx AsyncClient
├── scripts/
│   ├── setup.sh
│   ├── run.sh
│   ├── test.sh
│   └── down.sh
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## How to run

```bash
cp .env.example .env
./scripts/run.sh        # starts via Docker Compose
```

The API is available at `http://localhost:8000`.

## How to test

```bash
./scripts/test.sh
```

Or locally (after `./scripts/setup.sh`):

```bash
pytest
```

## API reference

### `POST /submit-data`

Accepts a validated JSON payload.

**Request body:**

| Field     | Type                              | Constraints                              |
|-----------|-----------------------------------|------------------------------------------|
| `user_id` | string                            | `^[a-zA-Z0-9_-]+$`, max 64 chars        |
| `action`  | `"read" \| "write" \| "delete"`   | only these three values                  |
| `content` | string                            | 1–500 chars                              |
| `tags`    | list[string] \| null              | optional; each tag: `^[a-z0-9_-]{1,32}$`|

**Responses:**

| Status | Meaning                                                      |
|--------|--------------------------------------------------------------|
| 200    | Submission accepted and validated                            |
| 400    | Semantic violation (injection pattern, bad tag format)       |
| 422    | Schema violation (wrong type, missing field, unknown field)  |

**Valid example:**

```bash
curl -s -X POST http://localhost:8000/submit-data \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice_01","action":"write","content":"Store report summary"}' \
  | jq
```

```json
{
  "status": "accepted",
  "message": "Data passed schema enforcement checks",
  "validated_action": "write",
  "user_id": "alice_01"
}
```

**Extra field (rejected 422):**

```bash
curl -s -X POST http://localhost:8000/submit-data \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","action":"read","content":"ok","injected":"extra"}' \
  | jq '.detail[0].msg'
# "Extra inputs are not permitted"
```

**SQL injection (rejected 400):**

```bash
curl -s -X POST http://localhost:8000/submit-data \
  -H "Content-Type: application/json" \
  -d '{"user_id":"attacker","action":"write","content":"SELECT * FROM users"}' \
  | jq '.detail'
# "Content contains disallowed patterns"
```

### `GET /health`

```json
{ "status": "ok", "app_name": "...", "app_env": "local" }
```

## Environment variables

| Variable         | Default               | Notes                    |
|------------------|-----------------------|--------------------------|
| `APP_NAME`       | `FastAPI POC Starter` |                          |
| `APP_ENV`        | `local`               |                          |
| `API_HOST`       | `0.0.0.0`             |                          |
| `API_PORT`       | `8000`                |                          |
| `OPENAI_API_KEY` | _(empty)_             | Not used by this POC     |

## Key limitations

- The injection pattern list is illustrative, not exhaustive. Production systems should use dedicated WAF rules or a library such as `bleach` for sanitisation.
- Content is rejected rather than sanitised — appropriate for strict enforcement but may need adjustment if legitimate content happens to match patterns.
- No authentication or rate-limiting — this POC focuses solely on input schema enforcement.

## Related patterns

- **01 — Untrusted Data Boundary** — isolating untrusted input at the system edge
- **03 — Output Schema Validation** — applying the same discipline to responses
- **04 — Structured Tool Allowlist** — whitelisting permitted tool calls in agentic pipelines
