import pytest

from apps.users.models import User

from .factories import PostFactory


@pytest.fixture
def sara(db):
    return User.objects.create_user(username="sara", email="sara@example.com", password="pass12345!")


def test_create_and_list(client, sara):
    client.force_login(sara)
    created = client.post("/api/v1/posts/", {"title": "Hello"}, content_type="application/json")
    assert created.status_code == 201
    listed = client.get("/api/v1/posts/")
    assert listed.json()["count"] == 1


def test_users_see_only_their_own_posts(auth_client, user):
    other_post = PostFactory()
    PostFactory(author=user)
    assert auth_client.get("/api/v1/posts/").json()["count"] == 1
    assert auth_client.get(f"/api/v1/posts/{other_post.id}/").status_code == 404
    assert auth_client.delete(f"/api/v1/posts/{other_post.id}/").status_code == 404


def test_update_and_delete(auth_client):
    post_id = auth_client.post("/api/v1/posts/", {"title": " Draft "}).json()["id"]
    assert auth_client.patch(f"/api/v1/posts/{post_id}/", {"title": "Final"}).json()["title"] == "Final"
    assert auth_client.delete(f"/api/v1/posts/{post_id}/").status_code == 204
