"""Staging and production. Every required variable has no default, so a missing one stops startup with
`ImproperlyConfigured: Set the <NAME> environment variable`."""

import sentry_sdk

from .base import *  # noqa: F403
from .base import DATABASES, LOGGING, env

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")
FRONTEND_URL = env("FRONTEND_URL").rstrip("/")
# API docs: staff only unless the task definition turns them on (staging does).
API_DOCS_PUBLIC = env.bool("API_DOCS_PUBLIC", default=False)

# Database: RDS with SSL.
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"

# Redis: ElastiCache with in-transit encryption, so a rediss:// URL.
REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "backend",
    }
}
CELERY_BROKER_URL = REDIS_URL
CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": "required"} if REDIS_URL.startswith("rediss://") else None

# HTTPS behind the ALB.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Client IP for the login lockout: the ALB appends the real client IP to X-Forwarded-For.
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]

# Files: uploads are private in S3 (presigned URLs); static files are served through CloudFront.
AWS_REGION = env("AWS_REGION")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = AWS_REGION
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

# Email through Amazon SES, using the task role (no keys).
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
ANYMAIL = {"AMAZON_SES_CLIENT_PARAMS": {"region_name": AWS_REGION}}
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL")

# Logs as JSON lines for CloudWatch.
LOGGING["handlers"]["console"]["formatter"] = "json"

# Errors to Sentry, when a DSN is set. The Django and Celery integrations turn on automatically.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,
    )
