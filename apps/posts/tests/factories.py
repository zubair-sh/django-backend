import factory

from apps.posts.models import Post
from apps.users.tests.factories import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=4)
    body = factory.Faker("paragraph")
