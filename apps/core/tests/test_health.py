import json
import logging

from apps.core.logging import JsonFormatter


def test_health_ok(client, db):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ignores_allowed_hosts(client, db):
    response = client.get("/health/", HTTP_HOST="10.0.1.23")
    assert response.status_code == 200


def test_json_formatter():
    record = logging.makeLogRecord({"name": "app", "levelname": "INFO", "msg": "hi %s", "args": ("there",)})
    line = json.loads(JsonFormatter().format(record))
    assert line["message"] == "hi there"
    assert line["level"] == "INFO"
