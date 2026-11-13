from rest_framework import viewsets

from apps.posts import services
from apps.posts.models import Post

from .serializers import PostSerializer


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # schema generation has no signed-in user
            return Post.objects.none()
        return Post.objects.filter(author=self.request.user)  # users see only their own posts

    def perform_create(self, serializer):
        serializer.instance = services.create_post(author=self.request.user, **serializer.validated_data)
