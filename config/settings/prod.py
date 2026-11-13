"""Staging and production. Every required variable has no default, so a missing one stops startup with
`ImproperlyConfigured: Set the <NAME> environment variable`."""

import sentry_sdk

from .base import *  # noqa: F403
from .base import DATABASES, LOGGING, env

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Database: RDS with SSL.
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"

# HTTPS behind the ALB.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Files: uploads are private in S3 (presigned URLs); static files are served through CloudFront.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_REGION")
CDN_DOMAIN = env("CDN_DOMAIN")
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "location": "media",
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
        },
    },
    "staticfiles": {"BACKEND": "apps.core.storages.StaticStorage"},
}
STATIC_URL = f"https://{CDN_DOMAIN}/"

# Logs as JSON lines for CloudWatch.
LOGGING["handlers"]["console"]["formatter"] = "json"

# Errors to Sentry, when a DSN is set.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,
    )
