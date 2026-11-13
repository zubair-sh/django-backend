import pytest
from django.test import override_settings

from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_docs_and_schema_are_served(client):
    assert client.get("/api/v1/docs/").status_code == 200
    schema = client.get("/api/v1/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json").json()
    assert "jwtAuth" in schema["components"]["securitySchemes"]


def test_schema_documents_login_response_and_public_endpoints(client):
    schema = client.get("/api/v1/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json").json()
    login = schema["paths"]["/api/v1/auth/login/"]["post"]
    assert login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/TokenPair")
    assert {"401", "429"} <= set(login["responses"])
    # Public endpoints show no lock icon in Swagger.
    assert schema["paths"]["/api/v1/auth/register/"]["post"].get("security") in (None, [], [{}])


@override_settings(API_DOCS_PUBLIC=False)
def test_docs_are_staff_only_when_not_public(client):
    assert client.get("/api/v1/docs/").status_code in (401, 403)
    client.force_login(UserFactory())
    assert client.get("/api/v1/schema/").status_code == 403
    client.force_login(UserFactory(is_staff=True))
    assert client.get("/api/v1/docs/").status_code == 200
    assert client.get("/api/v1/schema/").status_code == 200
