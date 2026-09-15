# lawsuit-parser
Parsing util for retrieving legal information about a company using its Taxpayer Identification Number (INN)

## Features

- 🔍 Parse company data from multiple sources
- 💾 Store results in PostgreSQL database
- ⚙️ Configurable sources via JSON settings
- 🔄 Retry logic with exponential backoff
- 📊 Structured logging
- 🐳 Docker support
- 🧪 Comprehensive test coverage

## Supported Sources

- Source 1: [Description]
- Source 2: [Description]
- Source N: [Description]

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker (optional)
- Redis (optional, for caching)

## Installation

### Using Pip

```bash
# Clone repository
git clone https://github.com/yourusername/company-info-parser.git
cd company-info-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Using Docker

### Build and run with Docker Compose
docker-compose --profile full up -d

### Run CLI commands
docker-compose --profile cli run --rm app-cli python -m src.main --parse-inn 1234567890

## Configuration

1. Copy .env.example to .env and update with your settings:
```
cp .env.example .env
```
2. Edit src/config/settings.json to configure:
* Enabled data sources

* Source-specific parameters (URLs, headers, timeouts)

* Database connection pool settings

* Logging configuration

## Usage

### CLI Interface

```bash
# Parse a single INN
python -m src.main --parse-inn 1234567890

# Parse multiple INNs from file
python -m src.main --parse-file inns.txt

# Initialize database
python -m src.main --init-db

# Run as web server
python -m src.main --run-server

# Show help
python -m src.main --help
```

### Programmatic Usage
```python
from src.services.parser_service import ParserService
from src.database.db_manager import DatabaseManager

# Initialize
db = DatabaseManager()
service = ParserService(db)

# Parse company
result = await service.parse_company("1234567890")
print(result)
```

## Database Schema

### Companies Table
* inn (Primary Key)

* name

* legal_address

* registration_date

* status

* created_at

* updated_at

### Company Sources Table

* id (Primary Key)

* inn (Foreign Key)

* source_name

* data (JSONB)

* parsed_at

### Parsing Attempts Table

* id (Primary Key)

* inn

* source_name

* status

* error_message

* attempted_at

* duration_ms

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_parsers.py
```

### Adding New Sources

1. Create a new parser class in `src/parsers/`:
```python
from src.parsers.base_parser import BaseParser

class NewSourceParser(BaseParser):
    def parse(self, inn):
        # Implement parsing logic
        pass
```

2. Add configuration to `settings.json`:
```JSON
{
  "sources": {
    "new_source": {
      "enabled": true,
      "url": "https://example.com/api",
      "parser_class": "NewSourceParser"
    }
  }
}
```

## Logging

Logs are stored in logs/app.log with rotation:

* Max size: 10 MB

* Backup count: 5

* Log level: Configurable in .env

## Monitoring

### Health Check
```text
GET /health
```

### Metrics (if enabled)
```text
GET /metrics
```