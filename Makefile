# Commands run inside the web container by default. Without Docker (after `uv sync`): make test RUN="uv run"
RUN ?= docker compose run --rm web
PROD_IMAGE ?= backend:local

.DEFAULT_GOAL := help
.PHONY: help setup env up down logs restart-worker shell migrate migrations superuser test lint format audit build-prod

help: ## List every command
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: .env ## One-time: install dependencies locally (for your editor) and the git hooks
	uv sync
	uv run pre-commit install

.env:
	cp .env.example .env

env: .env ## Create .env from .env.example if it's missing

up: .env ## Build and start Django, the worker, Postgres, Redis and Mailpit
	docker compose up --build

down: ## Stop the containers
	docker compose down

logs: ## Follow container logs
	docker compose logs -f

restart-worker: ## Restart the Celery worker after changing a task
	docker compose restart worker

shell: .env ## Open a Django shell (shell_plus: models already imported)
	$(RUN) python manage.py shell_plus

migrate: .env ## Apply migrations
	$(RUN) python manage.py migrate

migrations: .env ## Create migrations after a model change
	$(RUN) python manage.py makemigrations

superuser: .env ## Create an admin user
	$(RUN) python manage.py createsuperuser

test: .env ## Run pytest with coverage against Postgres (config.settings.test)
	$(RUN) pytest --cov

lint: .env ## ruff check and ruff format --check
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format: .env ## Fix lint issues and format the code
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

audit: ## Check dependencies for known vulnerabilities
	uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/requirements-audit.txt
	uvx pip-audit --strict --no-deps --disable-pip -r /tmp/requirements-audit.txt

build-prod: ## Build the production image locally
	docker build -f docker/Dockerfile --target prod -t $(PROD_IMAGE) .
