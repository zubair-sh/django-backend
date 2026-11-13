import pytest

from apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sara", email="sara@example.com", password="pass12345!")


def test_create_and_list(client, user):
    client.force_login(user)
    created = client.post("/api/v1/posts/", {"title": "Hello"}, content_type="application/json")
    assert created.status_code == 201
    listed = client.get("/api/v1/posts/")
    assert listed.json()["count"] == 1


def test_users_see_only_their_own_posts(client, user):
    other = User.objects.create_user(username="ali", email="ali@example.com", password="pass12345!")
    client.force_login(other)
    post_id = client.post("/api/v1/posts/", {"title": "Ali's"}, content_type="application/json").json()["id"]

    client.force_login(user)
    assert client.get("/api/v1/posts/").json()["count"] == 0
    assert client.get(f"/api/v1/posts/{post_id}/").status_code == 404
    assert client.delete(f"/api/v1/posts/{post_id}/").status_code == 404


def test_update_and_delete(client, user):
    client.force_login(user)
    post_id = client.post("/api/v1/posts/", {"title": " Draft "}, content_type="application/json").json()["id"]
    updated = client.patch(f"/api/v1/posts/{post_id}/", {"title": "Final"}, content_type="application/json")
    assert updated.json()["title"] == "Final"
    assert client.delete(f"/api/v1/posts/{post_id}/").status_code == 204
