from axes.handlers.proxy import AxesProxyHandler
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from apps.users import services

from .serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    UserSerializer,
)


class AuthThrottleMixin:
    throttle_scope = "auth"

    def get_throttles(self):
        return [*super().get_throttles(), ScopedRateThrottle()]


class LoginView(AuthThrottleMixin, TokenObtainPairView):
    """Email + password in; access and refresh tokens out. After 5 failures the account is locked for this IP
    for 15 minutes, and the response is 429."""

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            email = str(request.data.get("email", "")).strip().lower()
            if AxesProxyHandler.is_locked(request._request, {"email": email}):
                return Response(
                    {"detail": "Too many failed login attempts. Try again in 15 minutes."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            raise


class RefreshView(AuthThrottleMixin, TokenRefreshView):
    """Refresh token in; a new access token and a new refresh token out (the old refresh token stops working)."""


class LogoutView(AuthThrottleMixin, TokenBlacklistView):
    """Refresh token in; that token stops working."""


class RegisterView(AuthThrottleMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: RegisterResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {"access": str(refresh.access_token), "refresh": str(refresh)},
            },
            status=status.HTTP_201_CREATED,
        )


class PasswordResetRequestView(AuthThrottleMixin, APIView):
    """Always answers 202, whether or not the email has an account."""

    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses={202: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(email=serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    """uid and token come from the emailed link. Success signs the user out on every device."""

    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.reset_password(**serializer.validated_data)
        except services.InvalidResetLink:
            return Response({"detail": "This reset link is invalid or has expired."}, status=400)
        except DjangoValidationError as exc:
            return Response({"new_password": exc.messages}, status=400)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(AuthThrottleMixin, APIView):
    """Signs the user out on every device; the app should log in again with the new password."""

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(user=request.user, new_password=serializer.validated_data["new_password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """The signed-in user's own profile."""

    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.instance = services.update_profile(user=self.request.user, **serializer.validated_data)
