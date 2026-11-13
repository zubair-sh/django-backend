from axes.handlers.proxy import AxesProxyHandler
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from apps.core.schema import RATE_LIMITED, VALIDATION_ERROR, error
from apps.users import services

from .serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserSerializer,
)


class AuthThrottleMixin:
    throttle_scope = "auth"

    def get_throttles(self):
        return [*super().get_throttles(), ScopedRateThrottle()]


@extend_schema_view(
    post=extend_schema(
        summary="Log in",
        responses={
            200: TokenPairSerializer,
            401: error("Wrong email or password"),
            429: error("Too many attempts: 5 failures lock the account for this IP for 15 minutes"),
        },
    )
)
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


@extend_schema_view(
    post=extend_schema(
        summary="Refresh tokens",
        responses={
            200: TokenPairSerializer,
            401: error("Refresh token expired, invalid or already used"),
            429: RATE_LIMITED,
        },
    )
)
class RefreshView(AuthThrottleMixin, TokenRefreshView):
    """Refresh token in; a new access token and a new refresh token out (the old refresh token stops working)."""


@extend_schema_view(
    post=extend_schema(
        summary="Log out",
        responses={
            200: OpenApiResponse(description="Signed out"),
            401: error("Token invalid or already used"),
            429: RATE_LIMITED,
        },
    )
)
class LogoutView(AuthThrottleMixin, TokenBlacklistView):
    """Refresh token in; that token stops working."""


class RegisterView(AuthThrottleMixin, APIView):
    authentication_classes = ()
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Create an account",
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer, 400: VALIDATION_ERROR, 429: RATE_LIMITED},
    )
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

    authentication_classes = ()
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Request a password reset email",
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(description="Accepted"), 400: VALIDATION_ERROR, 429: RATE_LIMITED},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(email=serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    """uid and token come from the emailed link. Success signs the user out on every device."""

    authentication_classes = ()
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Set a new password from the emailed link",
        request=PasswordResetConfirmSerializer,
        responses={
            204: OpenApiResponse(description="Password changed; all sessions signed out"),
            400: OpenApiResponse(description="Link invalid or expired, or the new password is too weak"),
            429: RATE_LIMITED,
        },
    )
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

    @extend_schema(
        summary="Change password",
        request=PasswordChangeSerializer,
        responses={
            204: OpenApiResponse(description="Password changed; all sessions signed out"),
            400: VALIDATION_ERROR,
            401: error("Not signed in"),
            429: RATE_LIMITED,
        },
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(user=request.user, new_password=serializer.validated_data["new_password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(summary="Get my profile"),
    patch=extend_schema(summary="Update my name"),
)
class MeView(generics.RetrieveUpdateAPIView):
    """The signed-in user's own profile."""

    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.instance = services.update_profile(user=self.request.user, **serializer.validated_data)
