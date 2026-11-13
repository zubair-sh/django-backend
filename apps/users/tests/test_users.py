import pytest
from django.db import IntegrityError

from apps.users.models import User

from .factories import UserFactory


def test_me_requires_login(api_client, db):
    assert api_client.get("/api/v1/users/me/").status_code == 401


def test_me_returns_profile(auth_client, user):
    response = auth_client.get("/api/v1/users/me/")
    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_me_updates_name_but_not_email(auth_client, user):
    response = auth_client.patch("/api/v1/users/me/", {"first_name": "  Sara ", "email": "other@example.com"})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Sara"
    assert user.email != "other@example.com"


def test_email_is_unique_and_lowercased(db):
    UserFactory(email="Sara@Example.com")
    assert User.objects.filter(email="sara@example.com").exists()
    with pytest.raises(IntegrityError):
        UserFactory(email="sara@example.com")


def test_session_login_still_works_for_admin_users(client, user):
    client.force_login(user)
    assert client.get("/api/v1/users/me/").status_code == 200
