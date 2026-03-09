# POC 03 — Parameterized Queries

## What it demonstrates

This POC shows how **parameterized queries** (also called prepared statements) structurally prevent SQL injection by separating SQL code from user-supplied data.

When a query is executed via the database driver's parameterized API, user input is passed as a *value* — never spliced into the SQL string. This means a payload like `' OR '1'='1` is treated as a literal string, not SQL syntax.

## Why it matters

SQL injection has topped vulnerability rankings for decades. The root cause is almost always string interpolation — constructing SQL by concatenating user input directly into a query string. Parameterized queries eliminate this class of vulnerability entirely, at the driver level, with zero regex or escaping logic needed.

## Architecture overview

```
POST /api/execute-query
        │
        ▼
   ExecuteQueryRequest  (Pydantic validation)
        │
        ▼
   QueryService.execute(query, parameters)
        │  ├─ _validate_statement()  ← allowlist check (defence in depth)
        │  └─ conn.execute(query, parameters)  ← driver-level parameterized binding
        │
        ▼
   ExecuteQueryResponse (rows, rows_affected, error)
```

The core component is `QueryService` in `app/services/query_service.py`. It wraps a SQLite connection and exposes a single `execute(query, parameters)` method. The SQLite driver substitutes `?` placeholders with parameter values using C-level escaping — the SQL string and the data are never concatenated.

A secondary defence layer (`_validate_statement`) rejects DDL and other non-CRUD statement types, limiting the blast radius of misuse.

## Project structure

```
.
├── app/
│   ├── main.py                  ← FastAPI app wiring
│   ├── api/
│   │   └── routes.py            ← /execute-query and /seed endpoints
│   ├── models/
│   │   └── schemas.py           ← Pydantic request / response models
│   └── services/
│       └── query_service.py     ← parameterized query logic
├── core/
│   └── config.py                ← pydantic-settings config
├── tests/
│   ├── test_health.py
│   ├── test_query_service.py    ← unit tests (injection prevention, CRUD)
│   └── test_api.py              ← async API-level tests
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
./scripts/run.sh
```

The app is available at `http://localhost:8000`.

### Seed demo data

```bash
curl -X POST http://localhost:8000/api/seed
```

### Execute a parameterized query

```bash
curl -X POST http://localhost:8000/api/execute-query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE role = ?", "parameters": ["admin"]}'
```

### Injection attempt (safely neutralised)

```bash
curl -X POST http://localhost:8000/api/execute-query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE username = ?", "parameters": ["'\'' OR '\''1'\''='\''1"]}'
```

Returns zero rows — the tautology payload is treated as a literal username string.

## How to test

```bash
./scripts/test.sh
```

The test suite covers:

- Correct CRUD execution with parameterized binding
- Classic tautology injection (`' OR '1'='1`) → zero rows
- UNION injection payload → zero rows
- DROP TABLE injection payload → table survives
- DDL statement allowlist rejection
- API-level happy paths and error handling

## Environment variables

| Variable        | Default               | Notes                          |
|-----------------|-----------------------|--------------------------------|
| `APP_NAME`      | `FastAPI POC Starter` |                                |
| `APP_ENV`       | `local`               |                                |
| `API_HOST`      | `0.0.0.0`             |                                |
| `API_PORT`      | `8000`                |                                |
| `OPENAI_API_KEY`| _(empty)_             | Not used by this POC           |

## Key limitations

- The database is **in-memory** (`:memory:`). Data resets on every restart. A production system would use a persistent file path or a proper RDBMS.
- The allowlist (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) is intentionally restrictive for a demo. Real applications define access at the connection/role level in the DB itself.
- Multi-statement execution is not supported (SQLite's `execute()` raises on `;`-separated statements).

## Next logical POCs / related patterns

- **04 — Output schema validation** — validate LLM-generated SQL before execution
- **05 — Tool allowlist enforcement** — restrict which functions an agent can call
- **06 — Input sanitisation layer** — additional preprocessing before parameterized binding
