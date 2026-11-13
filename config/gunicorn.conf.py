"""Gunicorn settings for the prod image. Size workers with env vars: on Fargate, os.cpu_count() reports the
host's CPUs, not the task's vCPUs, so it can't be used to size workers."""

import os

bind = "0.0.0.0:8000"
worker_class = "gthread"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

timeout = 30  # a request stuck longer than this kills the worker
graceful_timeout = 25  # finish in-flight requests on deploy; keep below the ECS stopTimeout
keepalive = 75  # above the ALB idle timeout (60s), or the ALB returns occasional 502s

# Recycle workers now and then, so slow memory growth never takes a task down.
max_requests = 1000
max_requests_jitter = 100

forwarded_allow_ips = "*"  # only the ALB can reach the container (app-sg)
accesslog = None  # apps.core.middleware.RequestIdMiddleware logs each request with its request ID
errorlog = "-"
