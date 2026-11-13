from django.conf import settings
from rest_framework.permissions import BasePermission


class CanViewApiDocs(BasePermission):
    """API docs are open when API_DOCS_PUBLIC is on (dev, staging); otherwise staff only (production).
    Staff sign in through the admin, then open the docs in the same browser."""

    def has_permission(self, request, view):
        if settings.API_DOCS_PUBLIC:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
