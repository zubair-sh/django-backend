"""Shared pieces for API docs (drf-spectacular)."""

from drf_spectacular.utils import OpenApiResponse
from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


def error(description: str) -> OpenApiResponse:
    return OpenApiResponse(ErrorSerializer, description=description)


VALIDATION_ERROR = OpenApiResponse(
    description='Invalid input: an object of field name → list of messages, e.g. {"email": ["..."]}'
)
RATE_LIMITED = error("Too many requests; retry after the time in the Retry-After header")
