import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.database.db_manager import DatabaseManager


@pytest.fixture(scope='function')
def in_memory_db():
    """Fresh in-memory SQLite database per test."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    db = DatabaseManager.__new__(DatabaseManager)
    db.engine = engine
    db.SessionLocal = Session

    yield {'db': db, 'engine': engine, 'session_factory': Session}

    engine.dispose()


@pytest.fixture(scope='function')
def test_client(in_memory_db, monkeypatch):
    """FastAPI TestClient with DB swapped for in-memory SQLite.

    Patches src.api.dependencies.get_db and get_query_service so the routes
    use the in-memory database instead of the real Postgres.
    """
    from src.api import dependencies as deps
    from src.api.app import create_app
    from src.database.db_manager import DatabaseManager
    from src.services.query_service import QueryService

    # Build a QueryService that uses the in-memory DB
    test_db = in_memory_db['db']
    test_query = QueryService(test_db)

    # Replace the dependency providers
    monkeypatch.setattr(deps, 'get_db', lambda: test_db)
    monkeypatch.setattr(deps, 'get_query_service', lambda: test_query)
    monkeypatch.setattr(deps, 'get_config_manager', lambda: _FakeConfigManager())
    monkeypatch.setattr(deps, 'get_parser_service', lambda: _FakeParserService())

    app = create_app()

    # Override FastAPI's dependency-injection layer too
    app.dependency_overrides[deps.get_db] = lambda: test_db
    app.dependency_overrides[deps.get_query_service] = lambda: test_query

    with TestClient(app) as client:
        yield client


class _FakeConfigManager:
    def get_sources(self):
        return {}

    def get_db_config(self):
        return {}


class _FakeParserService:
    parser_factory = None