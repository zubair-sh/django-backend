import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


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
