# django-backend

Django 5.2 + Django REST Framework API, packaged for Docker and deployed to AWS ECS Fargate.

The full guide (setup, adding a feature, AWS, CI/CD, operations) is in the
[Django Backend — Complete Guide](https://claude.ai/artifact/PhjGRDisisMXHirVtyn8Ct).
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) is a short checklist version of the AWS part.

## Quick start

Needs Docker and `make`.

```bash
make up          # copies .env.example to .env, builds, starts on port 8000
# second terminal:
make migrate
make superuser
```

| What | URL |
| --- | --- |
| API docs (Swagger) | http://localhost:8000/api/v1/docs/ |
| Admin | http://localhost:8000/admin/ |
| Your profile | http://localhost:8000/api/v1/users/me/ (sign in through the admin first) |
| Posts | http://localhost:8000/api/v1/posts/ |
| Health check | http://localhost:8000/health/ |

Run `make help` for every command. `make test` and `make lint` run the same checks as CI.

## Layout

```
apps/
  core/            TimeStampedModel base class, /health/ middleware, JSON logging, S3 static storage
  users/           custom User (email is unique), /api/v1/users/me/
  posts/           worked example: CRUD at /api/v1/posts/
config/
  settings/        base.py, dev.py, test.py, prod.py
  urls.py          /admin/ and /api/v1/
deploy/            ECS task definitions (staging, production)
docker/Dockerfile  dev and prod build targets
scripts/           run-oneoff.sh: migrate etc. as an ECS task
.github/workflows/ ci.yml, deploy.yml, _release.yml
docs/              DEPLOYMENT.md
```
