import re

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.settings import api_settings

from .factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def login(api_client, email, password=DEFAULT_PASSWORD):
    return api_client.post("/api/v1/auth/login/", {"email": email, "password": password})


def test_register_returns_user_and_tokens(api_client):
    response = api_client.post(
        "/api/v1/auth/register/", {"email": "New@Example.com", "password": DEFAULT_PASSWORD, "first_name": "Sara"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    me = api_client.get("/api/v1/users/me/", HTTP_AUTHORIZATION=f"Bearer {body['tokens']['access']}")
    assert me.status_code == 200


def test_register_rejects_duplicate_email_and_weak_password(api_client):
    UserFactory(email="taken@example.com")
    dup = api_client.post("/api/v1/auth/register/", {"email": "TAKEN@example.com", "password": DEFAULT_PASSWORD})
    assert dup.status_code == 400 and "email" in dup.json()
    weak = api_client.post("/api/v1/auth/register/", {"email": "a@example.com", "password": "12345678"})
    assert weak.status_code == 400


def test_login_is_case_insensitive_and_refresh_rotates(api_client, user):
    response = login(api_client, user.email.upper())
    assert response.status_code == 200
    refresh = response.json()["refresh"]

    rotated = api_client.post("/api/v1/auth/refresh/", {"refresh": refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh"] != refresh
    # The old refresh token is blacklisted after rotation.
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}).status_code == 401


def test_logout_blacklists_refresh_token(api_client, user):
    refresh = login(api_client, user.email).json()["refresh"]
    assert api_client.post("/api/v1/auth/logout/", {"refresh": refresh}).status_code == 200
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": refresh}).status_code == 401


def test_wrong_password_is_rejected(api_client, user):
    assert login(api_client, user.email, "wrong-password").status_code == 401


def test_lockout_after_five_failures(api_client, user):
    for _ in range(5):
        login(api_client, user.email, "wrong-password")
    # Even the right password is refused while locked out; other accounts are unaffected.
    locked = login(api_client, user.email)
    assert locked.status_code == 429
    assert "access" not in locked.json()
    assert login(api_client, UserFactory().email).status_code == 200


def test_password_reset_flow(api_client, user, django_capture_on_commit_callbacks):
    old_refresh = login(api_client, user.email).json()["refresh"]

    with django_capture_on_commit_callbacks(execute=True):
        assert api_client.post("/api/v1/auth/password/reset/", {"email": user.email}).status_code == 202
    assert len(mail.outbox) == 1
    link = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    uid, token = re.search(r"uid=([^&]+)&token=(\S+)", link).groups()

    confirm = api_client.post(
        "/api/v1/auth/password/reset/confirm/", {"uid": uid, "token": token, "new_password": "brand-new-secret-77"}
    )
    assert confirm.status_code == 204
    assert login(api_client, user.email, "brand-new-secret-77").status_code == 200
    # Signed out everywhere, and the link works only once.
    assert api_client.post("/api/v1/auth/refresh/", {"refresh": old_refresh}).status_code == 401
    reused = api_client.post(
        "/api/v1/auth/password/reset/confirm/", {"uid": uid, "token": token, "new_password": "another-secret-88"}
    )
    assert reused.status_code == 400


def test_password_reset_for_unknown_email_looks_the_same(api_client):
    assert api_client.post("/api/v1/auth/password/reset/", {"email": "nobody@example.com"}).status_code == 202
    assert len(mail.outbox) == 0


def test_password_change(auth_client, api_client, user):
    wrong = auth_client.post(
        "/api/v1/auth/password/change/", {"current_password": "nope", "new_password": "brand-new-secret-77"}
    )
    assert wrong.status_code == 400
    ok = auth_client.post(
        "/api/v1/auth/password/change/", {"current_password": DEFAULT_PASSWORD, "new_password": "brand-new-secret-77"}
    )
    assert ok.status_code == 204
    assert login(api_client, user.email, "brand-new-secret-77").status_code == 200


def test_auth_endpoints_are_rate_limited(api_client, user, monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {**api_settings.DEFAULT_THROTTLE_RATES, "auth": "3/min"})
    cache.clear()
    codes = [api_client.post("/api/v1/auth/password/reset/", {"email": user.email}).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]
