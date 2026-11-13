import logging
import time

import sentry_sdk
from django.db import connection
from django.http import JsonResponse

from .request_id import reset_request_id, set_request_id

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("request")


class HealthCheckMiddleware:
    """Answers /health/ before host validation and HTTPS redirects, so the load balancer can call it by IP."""

    path = "/health/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != self.path:
            return self.get_response(request)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            logger.exception("Health check failed: database unreachable")
            return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
        return JsonResponse({"status": "ok"})


class RequestIdMiddleware:
    """Gives every request an ID: added to every log line, tagged in Sentry, returned as X-Request-ID.
    Also writes one log line per request (method, path, status, duration)."""

    header = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id, token = set_request_id(request.META.get(self.header))
        request.request_id = request_id
        sentry_sdk.set_tag("request_id", request_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
        finally:
            duration_ms = round((time.monotonic() - started) * 1000, 1)
        try:
            response["X-Request-ID"] = request_id
            user = getattr(request, "user", None)
            request_logger.info(
                "%s %s %s",
                request.method,
                request.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": user.pk if user is not None and user.is_authenticated else None,
                },
            )
            return response
        finally:
            reset_request_id(token)
