# Company Info Parser

A Python tool that parses information about companies from any number of web sources, keyed by INN (Taxpayer Identification Number). Each source is a self-contained parser module that the user writes, edits, or enables independently. Combines a CLI, an HTTP API, and a pluggable parser architecture. Designed to be consumed by downstream services such as a Telegram bot that tracks company changes over time.

---

## What is it?

A multi-source parser framework for company data. The framework provides:

- Dynamic loading of parser modules based on config
- A shared parsing pipeline (sessions, retries, timeouts, storage)
- Historical storage of every parse run in PostgreSQL
- A normalized diff between sessions to detect real changes
- Both a CLI and an HTTP API over the same services

Each parser is a black box to the framework. It can use HTTP, a browser, PDF extraction, or anything else — the framework only requires that it returns a JSON-serializable dict and declares its expected schema.

Sources are added or removed by editing `src/config/settings.json`. If a source is disabled, its module is not even imported. If a module is missing or misconfigured, it is skipped with a warning and the rest continue.

The project ships with a few example parsers for Russian government sources, but nothing in the framework is specific to them.

---

## Install

Requirements: Python 3.8+ (3.10/3.11 recommended), PostgreSQL 12+.

```bash
git clone https://github.com/yourusername/company-info-parser.git
cd company-info-parser

python3.11 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

Configure environment:

```bash
cp .env.example .env
```

Edit `.env` with your database credentials.

Create the database if it doesn't exist:

```bash
sudo -u postgres psql -c "CREATE DATABASE company_parser;"
```

Initialize tables:

```bash
python -m src.main --init-db
```

---

## Run

All commands run from the project root with `python -m src.main`.

### CLI

```bash
python -m src.main --parse-inn 7807234722
python -m src.main --parse-file inns.txt
python -m src.main --history 7807234722
python -m src.main --history 7807234722 --output history.json
python -m src.main --compare 7807234722 1 2
python -m src.main --list-sources
python -m src.main --init-db
```

### API server

```bash
python -m src.main --serve
```

Served at http://127.0.0.1:8000. Interactive docs at http://127.0.0.1:8000/docs.

Custom host/port:

```bash
python -m src.main --serve --host 0.0.0.0 --port 8080
```

Dev mode with auto-reload:

```bash
python -m src.main --serve --reload
```

### Docker

```bash
docker-compose up -d postgres redis api
```

API on http://localhost:8000. Stop with `docker-compose down`.

---

## Adding your own parser

Two steps, no code changes to the framework.

### Step 1 — Create the parser module

Create `src/parsers/yoursource_parser.py`:

```python
from typing import Dict, Any
from src.parsers.base_parser import BaseParser


class YourSourceParser(BaseParser):
    def __init__(self, source_name: str, config: Dict[str, Any]):
        super().__init__(source_name, config)

    def parse(self, inn: str) -> Dict[str, Any]:
        # Do whatever it takes: HTTP, browser automation, PDF parsing, etc.
        # Return any JSON-serializable dict.
        return {
            "inn": inn,
            "some_field": "some_value",
        }

    def get_data_schema(self) -> Dict[str, Any]:
        return {
            "inn": {"type": "string", "required": True},
            "some_field": {"type": "string", "required": False},
        }
```

### Step 2 — Register it in `src/config/settings.json`

```json
{
  "sources": {
    "yoursource": {
      "enabled": true,
      "module": "yoursource_parser",
      "class": "YourSourceParser",
      "timeout": 60,
      "retry_count": 3,
      "retry_delay": 2
    }
  }
}
```

Restart the API (or use `--reload`). The new source appears in `--list-sources`, in `GET /sources`, and runs alongside the others on every parse.

### What each parser owns

- Deciding what URLs to call and in what order
- Handling authentication, cookies, sessions, captchas
- Extracting and normalizing data into a dict
- Declaring its output shape via `get_data_schema()`

The framework does not impose any HTTP client, URL structure, or extraction method. Only two contracts exist:

1. Extend `BaseParser`
2. Return a JSON-serializable dict from `parse()`

### What the framework provides

- Dynamic module loading from `settings.json`
- Session tracking (every run gets a session ID)
- Retries, timeouts, per-source error handling
- Storage of raw output per `(inn, source, session)`
- History and diff endpoints
- Both CLI and API access

---

## Optional features

**API key authentication.** Off by default. To require it:

```bash
export API_KEY=your_secret
python -m src.main --serve
```

Clients must send `X-API-Key: your_secret`.

**Parallel parsing.** Run all enabled sources concurrently:

```bash
python -m src.main --parse-inn 7807234722 --parallel
```

Higher RAM usage — browser-based parsers each launch their own Chromium instance.

**Custom config path.** Use a different settings file:

```bash
python -m src.main --serve --config path/to/settings.json
```

**Redis.** Included in `docker-compose.yml` but not used by any code. Reserved for future caching and job-queue features.

---

## API table

All responses use the envelope `{ "ok": true, "data": ... }` or `{ "ok": false, "error": { "code", "message", "details" } }`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | Service and database health |
| GET | `/api/v1/sources` | List configured parsers |
| POST | `/api/v1/parses` | Parse one INN |
| POST | `/api/v1/parses/batch` | Parse many INNs |
| GET | `/api/v1/companies` | List all parsed INNs |
| GET | `/api/v1/companies/{inn}` | Company metadata |
| GET | `/api/v1/companies/{inn}/latest` | Latest data per source |
| GET | `/api/v1/companies/{inn}/history` | Session timeline |
| GET | `/api/v1/companies/{inn}/diff?from=&to=` | Field-level diff between two sessions |
| GET | `/api/v1/companies/{inn}/diff/latest` | Diff between the two most recent sessions |
| GET | `/api/v1/sessions` | List parse sessions |
| GET | `/api/v1/sessions/{id}` | Session metadata |
| GET | `/api/v1/sessions/{id}/data` | All data from a session |

**Error codes:** `INVALID_INN`, `INVALID_REQUEST`, `NOT_FOUND`, `PARSE_FAILED`, `SOURCE_NOT_FOUND`, `DATABASE_ERROR`, `INTERNAL_ERROR`, `UNAUTHORIZED`.

---

## Example parsers

The framework ships with a few example parsers for Russian government sources. They are not required — you can disable or delete them and add your own.

| Source | Description | Notes |
|--------|-------------|-------|
| nalog | FNS "Прозрачный бизнес" (pb.nalog.ru) | Tax status, debts, employees, revenue, tax regime |
| egrul | EGRUL PDF extract (egrul.nalog.ru) | Registration data, director, capital, OKVED, records |
| ras | Arbitration court cases (ras.arbitr.ru) | Blocked by site anti-bot (HTTP 451); kept as a reference implementation |

---

## Project layout

```
src/
├── api/           HTTP layer (FastAPI)
├── config/        settings.json + loader
├── database/      SQLAlchemy models + manager
├── parsers/       one module per data source
├── services/      business logic (parsing, queries, validation)
└── utils/         diff, validators, logger
```

---

## License

MIT