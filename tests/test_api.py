import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch('src.api.app.init_services'):
        from src.api.app import create_app
        app = create_app()

    mock_db = Mock()
    mock_session = Mock()
    mock_db.get_session.return_value = mock_session

    mock_query = Mock()
    mock_query.list_companies.return_value = {
        'items': [], 'total': 0, 'limit': 100, 'offset': 0,
    }
    mock_query.get_company.return_value = None
    mock_query.get_latest.return_value = None
    mock_query.get_history.return_value = {
        'items': [], 'total': 0, 'limit': 20, 'offset': 0,
    }
    mock_query.get_session.return_value = None
    mock_query.list_registered_sources.return_value = []

    mock_parser = Mock()

    from src.api.dependencies import (
        get_db, get_query_service, get_parser_service,
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_query_service] = lambda: mock_query
    app.dependency_overrides[get_parser_service] = lambda: mock_parser

    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get('/api/v1/health')
        assert resp.status_code == 200
        body = resp.json()
        assert body['ok'] is True
        assert 'status' in body['data']


class TestCompanies:
    def test_list_companies(self, client):
        resp = client.get('/api/v1/companies')
        assert resp.status_code == 200
        body = resp.json()
        assert body['ok'] is True
        assert body['data']['total'] == 0

    def test_invalid_inn_returns_error(self, client):
        resp = client.get('/api/v1/companies/invalid')
        assert resp.status_code == 400
        body = resp.json()
        assert body['ok'] is False
        assert body['error']['code'] == 'INVALID_INN'

    def test_company_not_found(self, client):
        resp = client.get('/api/v1/companies/7707083893')
        assert resp.status_code == 404
        body = resp.json()
        assert body['ok'] is False
        assert body['error']['code'] == 'NOT_FOUND'


class TestErrorEnvelope:
    def test_error_has_code_and_message(self, client):
        resp = client.get('/api/v1/companies/bad-inn')
        body = resp.json()
        assert body['ok'] is False
        assert 'code' in body['error']
        assert 'message' in body['error']