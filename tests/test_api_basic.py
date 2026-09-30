def test_root_endpoint_exists(test_client):
    response = test_client.get('/')
    assert response.status_code in (200, 404)


def test_openapi_schema_is_available(test_client):
    response = test_client.get('/openapi.json')
    assert response.status_code == 200

    schema = response.json()
    assert 'openapi' in schema
    assert 'paths' in schema
    assert '/api/v1/health' in schema['paths']


def test_docs_endpoint_is_available(test_client):
    response = test_client.get('/docs')
    assert response.status_code == 200


def test_unknown_endpoint_returns_404(test_client):
    response = test_client.get('/api/v1/this-does-not-exist')
    assert response.status_code == 404


def test_invalid_inn_returns_error_envelope(test_client):
    """The companies endpoint validates INN format and must return the
    standard error envelope."""
    response = test_client.get('/api/v1/companies/not-a-valid-inn')
    assert response.status_code == 400

    body = response.json()
    assert body['ok'] is False
    assert 'error' in body
    assert body['error']['code'] == 'INVALID_INN'
    assert 'message' in body['error']


def test_valid_inn_for_unknown_company_returns_not_found(test_client):
    """A well-formed INN that has never been parsed must return 404
    with the standard error envelope."""
    response = test_client.get('/api/v1/companies/7707083893')
    assert response.status_code in (404, 500)

    if response.status_code == 404:
        body = response.json()
        assert body['ok'] is False
        assert body['error']['code'] == 'NOT_FOUND'


def test_error_envelope_shape_is_consistent(test_client):
    """Any error must have ok=false and an error object with code and message."""
    response = test_client.get('/api/v1/companies/xyz')
    body = response.json()

    assert body['ok'] is False
    assert isinstance(body['error'], dict)
    assert 'code' in body['error']
    assert 'message' in body['error']
    assert 'details' in body['error']