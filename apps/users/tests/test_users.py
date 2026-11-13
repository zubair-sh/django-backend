import pytest

from apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sara", email="sara@example.com", password="pass12345!")


def test_me_requires_login(client, db):
    assert client.get("/api/v1/users/me/").status_code == 403


def test_me_returns_profile(client, user):
    client.force_login(user)
    response = client.get("/api/v1/users/me/")
    assert response.status_code == 200
    assert response.json()["email"] == "sara@example.com"


def test_me_updates_name_but_not_email(client, user):
    client.force_login(user)
    response = client.patch(
        "/api/v1/users/me/",
        {"first_name": "  Sara ", "email": "other@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Sara"
    assert user.email == "sara@example.com"


def test_email_is_unique(user):
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        User.objects.create_user(username="other", email="sara@example.com", password="pass12345!")
