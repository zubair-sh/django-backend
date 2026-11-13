from rest_framework import generics

from apps.users import services

from .serializers import UserSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """The signed-in user's own profile."""

    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.instance = services.update_profile(user=self.request.user, **serializer.validated_data)
