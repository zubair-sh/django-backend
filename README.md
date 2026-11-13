# django-backend

Django 5.2 + Django REST Framework API with JWT auth and a Celery worker, packaged for Docker and deployed to AWS
ECS Fargate.

The full guide (setup, adding a feature, AWS, CI/CD, operations) is in the
[Django Backend — Complete Guide](https://claude.ai/artifact/PhjGRDisisMXHirVtyn8Ct).
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) is a short checklist version of the AWS part.

## Quick start

Needs Docker, `make` and [uv](https://docs.astral.sh/uv/).

```bash
make setup       # once: installs packages locally (for your editor) and the git hooks
make up          # copies .env.example to .env, starts web, worker, Postgres, Redis and Mailpit
# second terminal:
make migrate
make superuser
```

| What | URL |
| --- | --- |
| API docs (Swagger) | http://localhost:8000/api/v1/docs/ |
| Admin | http://localhost:8000/admin/ |
| Emails sent locally (Mailpit) | http://localhost:8025 |
| Health check | http://localhost:8000/health/ |

Run `make help` for every command. `make test`, `make lint` and `make audit` run the same checks as CI.

## API

| Endpoint | What it does |
| --- | --- |
| `POST /api/v1/auth/register/` | Email + password → the new user and a token pair |
| `POST /api/v1/auth/login/` | Email + password → `access` (15 min) and `refresh` (7 days) tokens |
| `POST /api/v1/auth/refresh/` | Refresh token → new token pair; the old refresh token stops working |
| `POST /api/v1/auth/logout/` | Refresh token → that token stops working |
| `POST /api/v1/auth/password/reset/` | Email → a reset link by email (always 202) |
| `POST /api/v1/auth/password/reset/confirm/` | `uid`, `token` from the link + new password; signs out every device |
| `POST /api/v1/auth/password/change/` | Current + new password; signs out every device |
| `GET/PATCH /api/v1/users/me/` | The signed-in user's profile |
| `/api/v1/posts/` | Worked example: list, create, update, delete your own posts |

Send `Authorization: Bearer <access token>` on every other request. Auth endpoints allow 10 requests a minute per
client, and 5 wrong passwords lock that account for that IP for 15 minutes (429). Every response carries an
`X-Request-ID` header; send your own to trace a request through the logs.

## Layout

```
apps/
  core/            TimeStampedModel, /health/ and request-ID middleware, JSON logging, S3 static storage
  users/           custom User (signs in with email), auth API, password-reset email task
  posts/           worked example: CRUD at /api/v1/posts/
config/
  settings/        base.py, dev.py, test.py, prod.py
  celery.py        Celery app (worker: celery -A config worker)
  gunicorn.conf.py web server settings for the prod image
  urls.py          /admin/ and /api/v1/
deploy/            ECS task definitions: web and worker, staging and production
docker/Dockerfile  dev and prod build targets
scripts/           run-oneoff.sh (migrate etc. as an ECS task), deploy-service.sh (rollout with auto-rollback)
.github/workflows/ ci.yml, deploy.yml, _release.yml
docs/              DEPLOYMENT.md
```

Dependencies live in `pyproject.toml` and are locked in `uv.lock`. Add one with `uv add <package>`
(or `uv add --dev <package>`) and commit both files.
