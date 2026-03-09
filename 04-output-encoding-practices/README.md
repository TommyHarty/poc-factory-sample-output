# 04 — Output Encoding Practices

## What it demonstrates

This POC shows how **output encoding** prevents Cross-Site Scripting (XSS) attacks. When user-supplied text is reflected back through an API and later rendered in a browser, any embedded HTML or JavaScript must first be converted to safe HTML entities. This POC implements and tests that conversion using Python's standard `html.escape` wrapped in a focused service layer.

## Why it matters

XSS is one of the most common web vulnerabilities. An application that echoes user input verbatim in an HTML context allows attackers to inject `<script>` tags or event handlers. Output encoding — converting `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, `"` → `&quot;`, `'` → `&#x27;` — neutralises payloads before they reach the browser DOM.

## Architecture overview

```
POST /encode
     │
     ▼
app/api/routes.py        ← APIRouter, thin handler
     │
     ▼
app/services/encoder.py  ← html_encode() wraps html.escape()
     │
     ▼
EncodeResponse           ← Pydantic response model
```

## Project structure

```
.
├── app/
│   ├── main.py              ← FastAPI app, wires router
│   ├── api/
│   │   └── routes.py        ← POST /encode handler
│   ├── models/
│   │   └── schemas.py       ← EncodeRequest / EncodeResponse
│   └── services/
│       └── encoder.py       ← html_encode() core logic
├── core/
│   └── config.py            ← pydantic-settings Settings
├── tests/
│   ├── test_encoder.py      ← unit tests for encoder
│   └── test_api.py          ← API-level tests with httpx AsyncClient
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## How to run

```bash
cp .env.example .env
./scripts/run.sh          # starts via Docker Compose
```

Or directly:

```bash
docker compose up
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

### `POST /encode`

Accepts raw user text and returns its HTML-encoded equivalent.

**Request**

```json
{ "text": "<script>alert('XSS')</script>" }
```

**Response**

```json
{ "encoded_text": "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" }
```

**Edge cases**

| Input | Encoded output |
|---|---|
| `rock & roll` | `rock &amp; roll` |
| `<b>bold</b>` | `&lt;b&gt;bold&lt;/b&gt;` |
| `say "hi"` | `say &quot;hi&quot;` |
| `it's fine` | `it&#x27;s fine` |
| _(empty string)_ | _(empty string)_ |

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `APP_NAME` | `FastAPI POC Starter` | |
| `APP_ENV` | `local` | |
| `API_HOST` | `0.0.0.0` | |
| `API_PORT` | `8000` | |
| `OPENAI_API_KEY` | _(empty)_ | Not used by this POC |

## Key limitations

- This POC encodes for **HTML contexts** only. JavaScript string contexts, URL parameters, and CSS values require different encoding strategies.
- The encoding is applied at the API response layer. Real applications should encode at the point of rendering (template engine, React, etc.), not solely at the API boundary.
- No Content-Security-Policy header is configured — that is a complementary defence, not covered here.

## Related patterns

- `03-structured-tool-allowlist` — controls what actions the model may take
- `05-input-validation-guardrails` — validates inputs before they reach the model
- Content-Security-Policy middleware (next natural addition)
