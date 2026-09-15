# Company Info Parser

A Python tool for parsing legal and financial information about Russian companies from multiple government sources using their INN (Taxpayer Identification Number). Combines a CLI, an HTTP API, and a pluggable parser architecture — built to be consumed by downstream services such as a Telegram bot that tracks company changes over time.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Supported Sources](#supported-sources)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Database Setup](#database-setup)
8. [CLI Usage](#cli-usage)
9. [HTTP API](#http-api)
10. [Adding New Parsers](#adding-new-parsers)
11. [Docker Deployment](#docker-deployment)
12. [Testing](#testing)
13. [Project Structure](#project-structure)
14. [Troubleshooting](#troubleshooting)
15. [License](#license)

---

## Features

- **Multi-source parsing** — one company, many sources, all stored together per parsing session
- **Pluggable architecture** — each parser is a self-contained module; add a new source by dropping a file and editing `settings.json`
- **Historical sessions** — every parse run creates a new session; data is never overwritten, so you can track changes over time
- **Normalized diff** — compares two sessions and returns field-level changes, ignoring volatile fields (`parsed_at`, `url`, `_metadata`)
- **CLI + HTTP API** — same functionality available both ways
- **Optional API key auth** — off by default for local development; toggle via env var
- **Docker-ready** — full `docker-compose` stack with Postgres, Redis, and pgAdmin
- **Structured logging** — JSON logs with rotation
- **INN validation** — checksum verification before any parsing is attempted

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Consumer (Telegram bot)                   │
│                       separate repo                          │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP / JSON
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│  src/api/                                                    │
│   ├── app.py          — app factory                          │
│   ├── routes/         — endpoint handlers                    │
│   ├── dependencies.py — service injection                    │
│   ├── errors.py       — error codes + handler                │
│   └── schemas.py      — request/response models              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  src/services/                                               │
│   ├── parser_service.py   — orchestrates parse runs          │
│   ├── query_service.py    — read-only queries for the API    │
│   └── validation_service.py                                  │
└────────┬─────────────────────┬──────────────────┬────────────┘
         │                     │                  │
         ▼                     ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐
│  Parsers        │  │  Database       │  │  Utilities         │
│  src/parsers/   │  │  src/database/  │  │  src/utils/        │
│  ├── base       │  │  ├── models.py  │  │  ├── diff.py       │
│  ├── factory    │  │  └── db_mgr.py  │  │  ├── validators.py │
│  ├── nalog      │  │                 │  │  ├── logger.py     │
│  ├── egrul      │  │                 │  │  └── http_client.py│
│  └── ras        │  │                 │  │                    │
└─────────────────┘  └─────────────────┘  └────────────────────┘
```

### Key Concepts

- **Source** — a data origin (e.g. `nalog`, `egrul`). Each source has its own parser module and its own settings entry.
- **Parser** — a Python module in `src/parsers/` extending `BaseParser`. It's fully responsible for its own logic: URLs, navigation, extraction, and output shape.
- **Session** — one parse run. Every parse command creates a session; all data from that run is tagged with the session ID.
- **ParserData** — the raw JSON blob a parser returned, keyed by `(inn, source_name, session_id)`.
- **Diff** — the difference between two sessions for the same INN, filtered to remove volatile fields. This is what a notification system reacts to.

---

## Supported Sources

| Source | Description | Status |
|--------|-------------|--------|
| `nalog` | FNS "Прозрачный бизнес" (`pb.nalog.ru`) — tax status, debts, employees, revenue, tax regime | ✅ Working |
| `egrul` | EGRUL PDF extract (`egrul.nalog.ru`) — registration data, director, capital, OKVED, records | ✅ Working |
| `ras` | Arbitration court cases (`ras.arbitr.ru`) | ⚠️ Blocked by site anti-bot (HTTP 451) — see [Troubleshooting](#troubleshooting) |

---

## Requirements

- Python **3.8+** (3.10 or 3.11 recommended)
- PostgreSQL **12+**
- ~500 MB RAM per parser (uses headless Chromium via Playwright)
- (Optional) Docker and Docker Compose
- (Optional) Redis for future caching

---

## Installation

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/yourusername/company-info-parser.git
cd company-info-parser

python3.11 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install chromium
playwright install-deps     # Linux only
```

### 4. Configure

```bash
cp .env.example .env
```

Edit `.env` with your database credentials and other settings.

### 5. Initialize the database

```bash
python -m src.main --init-db
```

This creates the tables and registers the sources listed in `src/config/settings.json`.

---

## Configuration

### Environment Variables (`.env`)

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=company_parser
DB_USER=postgres
DB_PASSWORD=postgres

# API Server
API_HOST=127.0.0.1
API_PORT=8000
API_KEY=                      # leave blank for open access

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Sources (`src/config/settings.json`)

Enable or disable parsers by flipping `"enabled"`:

```json
{
  "sources": {
    "nalog": {
      "enabled": true,
      "module": "nalog_parser",
      "class": "NalogParser",
      "timeout": 90,
      "retry_count": 3,
      "retry_delay": 2,
      "rate_limit": { "requests_per_minute": 10 }
    },
    "egrul": {
      "enabled": true,
      "module": "egrul_parser",
      "class": "EgrulParser",
      "timeout": 90,
      "retry_count": 2,
      "retry_delay": 5
    }
  },
  "database": {
    "pool_size": 10,
    "max_overflow": 20,
    "echo": false
  },
  "processing": {
    "parallel_sources": false,
    "timeout_per_source": 90
  },
  "logging": {
    "level": "INFO",
    "file": "logs/app.log",
    "max_size_mb": 10,
    "backup_count": 5
  }
}
```

**Disabling a source is a hard removal** — the parser module isn't even imported, so no network calls are made and no data is written. If a source's module or class name is wrong, it's logged as a warning and skipped; the rest continue.

---

## Database Setup

### Local PostgreSQL

```bash
sudo -u postgres psql -c "CREATE DATABASE company_parser;"
sudo -u postgres psql -c "CREATE USER parser WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE company_parser TO parser;"
```

Then update `.env` and run:

```bash
python -m src.main --init-db
```

### Docker Compose (Postgres only)

```bash
docker-compose up -d postgres redis
python -m src.main --init-db
```

### Tables

| Table | Purpose |
|-------|---------|
| `companies` | Every INN ever parsed |
| `parsing_sessions` | One row per parse run |
| `parser_data` | Raw JSON per `(inn, source, session)` — the main data table |
| `parsing_attempts` | Success/failure per source per run, for diagnostics |
| `source_registry` | Which sources are registered and enabled |

### Inspect the Data

```bash
psql -U postgres -d company_parser -c "
SELECT session_id, source_name, parsed_at
FROM parser_data
WHERE inn = '7807234722'
ORDER BY parsed_at DESC;
"
```

Pretty-print a full JSON blob:

```bash
psql -U postgres -d company_parser -c "
SELECT jsonb_pretty(data::jsonb)
FROM parser_data
WHERE inn = '7807234722' AND source_name = 'egrul'
ORDER BY parsed_at DESC
LIMIT 1;
"
```

---

## CLI Usage

All commands run from the project root with `python -m src.main`.

### Initialize the database

```bash
python -m src.main --init-db
```

### List configured sources

```bash
python -m src.main --list-sources
```

Output:

```
Available Sources:
------------------------------------------------------------
Source               Enabled    Module               Class
------------------------------------------------------------
nalog                True       nalog_parser         NalogParser
egrul                True       egrul_parser         EgrulParser
ras                  False      ras_parser           RasParser
------------------------------------------------------------
Total: 3 sources, 2 enabled
```

### Parse a single INN

```bash
python -m src.main --parse-inn 7807234722
```

Runs every enabled source under one session. Output includes the session ID.

**With a specific source only:**

```bash
python -m src.main --parse-inn 7807234722 --source egrul
```

**In parallel (faster but higher RAM):**

```bash
python -m src.main --parse-inn 7807234722 --parallel
```

### Parse multiple INNs from a file

Create `inns.txt` with one INN per line:

```
7807234722
7707083893
```

Then run:

```bash
python -m src.main --parse-file inns.txt
```

### Show history for an INN

```bash
python -m src.main --history 7807234722
```

### Save history to JSON

```bash
python -m src.main --history 7807234722 --output exports/history_7807234722.json
```

The output file is UTF-8, indented, and grouped by session:

```json
{
  "inn": "7807234722",
  "total_sessions": 3,
  "sessions": [
    {
      "session_id": 1,
      "parsed_at": "2026-09-15T08:41:36.597206",
      "sources": {
        "nalog": { "...": "..." },
        "egrul": { "...": "..." }
      }
    }
  ]
}
```

### Compare two sessions

```bash
python -m src.main --compare 7807234722 1 2
```

### Run as HTTP API

```bash
python -m src.main --serve
```

See [HTTP API](#http-api) below.

### Help

```bash
python -m src.main --help
```

---

## HTTP API

The API is a thin FastAPI wrapper over the same services used by the CLI. It's intended for downstream consumers (the Telegram bot) that shouldn't talk to the database directly.

### Starting the server

```bash
python -m src.main --serve
```

With custom host/port:

```bash
python -m src.main --serve --host 0.0.0.0 --port 8080
```

With auto-reload (dev only):

```bash
python -m src.main --serve --reload
```

Interactive docs: `http://127.0.0.1:8000/docs`

### Authentication

The API is **open by default**. To require an API key, set `API_KEY` in your environment:

```bash
export API_KEY=your_secret_here
python -m src.main --serve
```

Then every request must include the header `X-API-Key: your_secret_here`.

### Response Envelope

Every successful response:

```json
{ "ok": true, "data": { ... } }
```

Every error:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INN",
    "message": "INN must be 10 or 12 digits",
    "details": { "inn": "abc" }
  }
}
```

HTTP status codes still apply (`400`, `404`, `409`, `500`), but the body always follows this shape.

### Endpoints

#### Health

```
GET /api/v1/health
→ { "ok": true, "data": { "status": "ok", "database": "connected" } }
```

#### Sources

```
GET /api/v1/sources
→ { "ok": true, "data": { "items": [
    { "name": "nalog", "enabled": true, "module": "nalog_parser", "class": "NalogParser", "registered": true },
    { "name": "egrul", "enabled": true, "module": "egrul_parser", "class": "EgrulParser", "registered": true }
  ], "total": 2 } }
```

#### Start a parse

```
POST /api/v1/parses
Body: { "inn": "7807234722", "sources": ["nalog", "egrul"], "parallel": false }
→ { "ok": true, "data": {
    "success": true,
    "session_id": 12,
    "total_sources": 2,
    "successful_sources": 2,
    "results": { ... }
  } }
```

**Batch:**

```
POST /api/v1/parses/batch
Body: { "inns": ["7807234722", "7707083893"] }
→ { "ok": true, "data": { "results": [ ... ], "total": 2 } }
```

#### List companies

```
GET /api/v1/companies?limit=100&offset=0
→ { "ok": true, "data": { "items": [
    { "inn": "7807234722", "first_parsed_at": "...", "last_parsed_at": "..." }
  ], "total": 1, "limit": 100, "offset": 0 } }
```

#### Company metadata

```
GET /api/v1/companies/{inn}
→ { "ok": true, "data": {
    "inn": "7807234722",
    "first_parsed_at": "...",
    "last_parsed_at": "...",
    "sessions_count": 3,
    "sources": ["nalog", "egrul"]
  } }
```

#### Latest data per source

```
GET /api/v1/companies/{inn}/latest?sources=nalog,egrul
→ { "ok": true, "data": {
    "inn": "7807234722",
    "session_id": 12,
    "sources": { "nalog": { ... }, "egrul": { ... } }
  } }
```

#### Session timeline

```
GET /api/v1/companies/{inn}/history?limit=20&offset=0
→ { "ok": true, "data": { "items": [
    { "session_id": 12, "parsed_at": "...", "sources": ["nalog", "egrul"] },
    { "session_id": 11, "parsed_at": "...", "sources": ["nalog"] }
  ], "total": 2, "limit": 20, "offset": 0 } }
```

#### Diff between two sessions

```
GET /api/v1/companies/{inn}/diff?from=11&to=12&sources=nalog,egrul
→ { "ok": true, "data": {
    "inn": "7807234722",
    "from_session_id": 11,
    "to_session_id": 12,
    "changed": true,
    "sources": {
      "nalog": {
        "changed": true,
        "fields": [
          { "field": "status", "type": "changed", "from": "действующая", "to": "в процессе реорганизации" }
        ],
        "changed_count": 1
      },
      "egrul": { "changed": false, "fields": [], "changed_count": 0 }
    }
  } }
```

#### Diff since last check

```
GET /api/v1/companies/{inn}/diff/latest
```

Compares the two most recent sessions for the INN. This is the endpoint the bot will use for "what changed since I last looked".

#### Sessions

```
GET /api/v1/sessions?limit=50&offset=0
GET /api/v1/sessions/{session_id}
GET /api/v1/sessions/{session_id}/data
```

### Client example (Python)

```python
import httpx

async def check_company(inn: str):
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Trigger a parse
        r = await client.post("/api/v1/parses", json={"inn": inn})
        r.raise_for_status()
        session_id = r.json()["data"]["session_id"]

        # Compare to previous run
        r = await client.get(f"/api/v1/companies/{inn}/diff/latest")
        diff = r.json()["data"]

        if diff["changed"]:
            for source, details in diff["sources"].items():
                for field in details["fields"]:
                    print(f"[{source}] {field['field']}: {field.get('from')} -> {field.get('to')}")
```

### Error Codes

| Code | Meaning |
|------|---------|
| `INVALID_INN` | INN format or checksum failed |
| `INVALID_REQUEST` | Malformed request body |
| `NOT_FOUND` | Company, session, or INN not found |
| `PARSE_FAILED` | Parser raised an error |
| `SOURCE_NOT_FOUND` | Requested source is not configured or not available |
| `DATABASE_ERROR` | Database operation failed |
| `INTERNAL_ERROR` | Unexpected server error |
| `UNAUTHORIZED` | Missing or invalid API key |

---

## Adding New Parsers

The parser architecture is designed to stay out of your way. Adding a new source requires **two steps**, no changes to the API, CLI, or service layer.

### Step 1 — Create the parser module

Create `src/parsers/newsource_parser.py`:

```python
from typing import Dict, Any
from src.parsers.base_parser import BaseParser


class NewSourceParser(BaseParser):
    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)

    def parse(self, inn: str) -> Dict[str, Any]:
        # Do whatever it takes: HTTP requests, browser automation, PDF parsing, etc.
        # Return a JSON-serializable dict.
        return {
            "inn": inn,
            "some_field": "some_value",
            # ... whatever this source provides
        }

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            "inn": {"type": "string", "required": True},
            "some_field": {"type": "string", "required": False},
        }
```

### Step 2 — Register it in `settings.json`

```json
{
  "sources": {
    "newsource": {
      "enabled": true,
      "module": "newsource_parser",
      "class": "NewSourceParser",
      "timeout": 60,
      "retry_count": 3,
      "retry_delay": 2
    }
  }
}
```

Restart the API (or use `--reload`). The new source appears in `--list-sources`, in `GET /sources`, and runs alongside the others on every parse.

If the module or class is missing, it's logged as a warning and skipped. The rest continue.

### What Each Parser Owns

Each parser is a black box to the rest of the system. It's responsible for:

- Deciding what URLs to call and in what order
- Handling authentication, cookies, sessions, captchas
- Extracting and normalizing data into a JSON-serializable dict
- Declaring its expected output via `get_data_schema()`

The framework **does not** impose any URL structure, HTTP client, or extraction method. Playwright, `requests`, `curl_cffi`, PDF parsing, Selenium — whatever the source needs.

---

## Docker Deployment

### Full stack with Postgres

```bash
docker-compose up -d postgres redis api
```

The API is served on `http://localhost:8000`.

### Dev mode with auto-reload

```bash
docker-compose --profile dev up api-dev
```

Served on `http://localhost:8001`.

### Run one-off CLI commands

```bash
docker-compose --profile cli run --rm cli --parse-inn 7807234722
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| `postgres` | 5432 | Database |
| `redis` | 6379 | Cache (reserved for future use) |
| `api` | 8000 | Production API server |
| `api-dev` | 8001 | Dev API with `--reload` |
| `cli` | — | Run CLI commands against the same DB |
| `pgadmin` | 5050 | Web UI for the database (`dev` profile only) |

### Access pgAdmin

```bash
docker-compose --profile dev up pgadmin
```

Open `http://localhost:5050` — login with `admin@company.com` / `admin_password`, then add a server pointing to host `postgres`, user `postgres`, password from your `.env`.

### Environment for Containers

Set these in your shell or in a `.env` file next to `docker-compose.yml`:

```bash
DB_NAME=company_parser
DB_USER=postgres
DB_PASSWORD=postgres_secure_password
REDIS_PASSWORD=redis_secure_password
API_KEY=                 # leave blank to disable auth
LOG_LEVEL=INFO
```

---

## Testing

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Run a specific file

```bash
pytest tests/test_api.py -v
pytest tests/test_diff.py -v
```

### Test markers

```bash
pytest -m unit          # unit tests only
pytest -m integration   # integration tests (require DB)
```

### Linting and formatting

```bash
make lint
make format
```

or manually:

```bash
flake8 src/ tests/
mypy src/ tests/
black src/ tests/
isort src/ tests/
```

---

## Project Structure

```
company-info-parser/
│
├── src/
│   ├── __init__.py
│   ├── main.py                         # CLI + API entry point
│   │
│   ├── api/                            # HTTP layer (FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── sources.py
│   │       ├── parses.py
│   │       ├── companies.py
│   │       └── sessions.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── config_manager.py
│   │   └── settings.json
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db_manager.py
│   │   ├── models.py
│   │   └── migrations/
│   │       └── __init__.py
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   ├── parser_factory.py
│   │   ├── nalog_parser.py
│   │   ├── egrul_parser.py
│   │   ├── ras_parser.py
│   │   ├── egrul_working_dir/
│   │   │   └── .gitkeep
│   │   └── ras_working_dir/
│   │       └── .gitkeep
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parser_service.py
│   │   ├── query_service.py
│   │   └── validation_service.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── diff.py
│   │   ├── http_client.py
│   │   ├── logger.py
│   │   └── validators.py
│   │
│   └── exceptions/
│       ├── __init__.py
│       └── custom_exceptions.py
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_diff.py
│   ├── test_parsers.py
│   └── test_services.py
│
├── logs/
│   └── .gitkeep
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pytest.ini
├── README.md
├── requirements.txt
└── setup.py
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'src'`

You're either running from inside `src/` or invoking the file directly. Always run from the project root with `-m`:

```bash
cd /path/to/company-info-parser
python -m src.main --init-db
```

If it persists, install the project in editable mode:

```bash
pip install -e .
```

### `playwright._impl._errors.TimeoutError`

Playwright's bundled Chromium may not be installed. Run:

```bash
playwright install chromium
```

### `ImportError: cannot import name 'X'`

Usually a stale `.pyc` cache. Clear it:

```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
```

### API server won't start — `Address already in use`

Something else is on port 8000. Either stop it or use another port:

```bash
python -m src.main --serve --port 8080
```

### `curl_cffi` not installed

The `ras` parser uses `curl_cffi` for TLS impersonation. Install it:

```bash
pip install curl_cffi
```

### `ras.arbitr.ru` returns HTTP 451

This is a deliberate anti-bot block from the site, not a bug in the parser. The site uses WASM-based browser fingerprinting, TLS fingerprinting, and captcha checks. Even a real Playwright session that successfully completes a search gets blocked on subsequent automated requests.

**Workarounds:**

1. **Manual cookie refresh.** Open `ras.arbitr.ru` in a regular browser, complete a search, export cookies, and feed them to the parser via a file. You'll need to refresh them periodically.
2. **Paid third-party API.** Several services provide clean JSON access to `ras.arbitr.ru` without captchas (e.g. `api-parser.ru`, `arbitr.mchanges.com`).
3. **Disable the `ras` source.** Set `"enabled": false` in `settings.json`. The other sources continue working.

### Empty `parser_data` after parsing

Check `parsing_attempts` for the errors:

```bash
psql -U postgres -d company_parser -c "
SELECT source_name, status, error_message, attempted_at
FROM parsing_attempts
WHERE inn = '7807234722'
ORDER BY attempted_at DESC
LIMIT 20;
"
```

### Database connection refused

- Verify Postgres is running: `sudo systemctl status postgresql` (Linux) or `brew services list` (macOS)
- Check `.env` credentials match your PostgreSQL setup
- Test directly: `psql -U postgres -d company_parser -c "SELECT 1"`

### Slow parsing

- Increase `timeout_per_source` in `settings.json`
- Disable unused sources
- Avoid `--parallel` on machines with limited RAM — each parser may launch a browser
- Both `nalog` and `egrul` use Playwright; running them in parallel means two Chromium instances at once

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Roadmap

- [ ] Redis-backed caching for repeated INN queries
- [ ] Prometheus metrics endpoint
- [ ] Migration to Alembic for schema versioning
- [ ] OpenAPI client generation for the Telegram bot
- [ ] Webhook notifications when parsing completes
- [ ] Additional sources (KAD Arbitr, FSSP, bank guarantees)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support

For questions, bugs, or feature requests, open an issue on GitHub.