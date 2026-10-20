def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_prefixed(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200


def test_readyz_reports_database_ok(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["checks"]["database"] == "ok"


def test_process_time_header_present(client):
    response = client.get("/healthz")
    assert "x-process-time-ms" in response.headers
    assert float(response.headers["x-process-time-ms"]) >= 0


def test_request_id_header_generated(client):
    response = client.get("/healthz")
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]


def test_request_id_header_echoed(client):
    response = client.get("/healthz", headers={"X-Request-ID": "test-123"})
    assert response.headers["x-request-id"] == "test-123"


def test_openapi_available_in_dev(client):
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_unknown_route_returns_structured_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
