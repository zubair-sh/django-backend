# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# ---- dev: used by docker compose; the project folder is mounted over /app ----
FROM base AS dev
COPY requirements/ requirements/
RUN pip install -r requirements/dev.txt
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- prod: the image that runs on ECS ----
FROM base AS prod
COPY requirements/ requirements/
RUN pip install -r requirements/prod.txt \
 && useradd --create-home --uid 1000 app
COPY --chown=app:app . .
USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--forwarded-allow-ips", "*"]
