import logging


def test_response_has_generated_request_id(client, db):
    response = client.get("/api/v1/users/me/")
    assert len(response["X-Request-ID"]) == 32


def test_incoming_request_id_is_kept(client, db):
    response = client.get("/api/v1/users/me/", HTTP_X_REQUEST_ID="frontend-abc-12345")
    assert response["X-Request-ID"] == "frontend-abc-12345"


def test_unsafe_request_id_is_replaced(client, db):
    response = client.get("/api/v1/users/me/", HTTP_X_REQUEST_ID="bad id\nwith newline")
    assert response["X-Request-ID"] != "bad id\nwith newline"


def test_request_is_logged_with_its_id(client, db, caplog):
    with caplog.at_level(logging.INFO, logger="request"):
        response = client.get("/api/v1/users/me/", HTTP_X_REQUEST_ID="trace-me-123456")
    record = next(r for r in caplog.records if r.name == "request")
    assert record.status == response.status_code == 401
    assert record.path == "/api/v1/users/me/"
