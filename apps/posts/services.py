from .models import Post


def create_post(*, author, title: str, body: str = "") -> Post:
    return Post.objects.create(author=author, title=title.strip(), body=body)
