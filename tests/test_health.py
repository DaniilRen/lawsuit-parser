def test_health_endpoint_returns_ok(test_client):
    response = test_client.get('/api/v1/health')
    assert response.status_code == 200

    body = response.json()
    assert body['ok'] is True
    assert 'data' in body
    assert body['data']['status'] == 'ok'


def test_health_endpoint_reports_database_status(test_client):
    response = test_client.get('/api/v1/health')
    body = response.json()

    assert 'database' in body['data']
    assert body['data']['database'] in ('connected', 'error')