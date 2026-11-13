# Commands run inside the web container by default. Without Docker: make test RUN=
RUN ?= docker compose run --rm web
PROD_IMAGE ?= backend:local

.DEFAULT_GOAL := help
.PHONY: help env up down logs shell migrate migrations superuser test lint format build-prod

help: ## List every command
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.env:
	cp .env.example .env

env: .env ## Create .env from .env.example if it's missing

up: .env ## Build and start Django and Postgres on port 8000
	docker compose up --build

down: ## Stop the containers
	docker compose down

logs: ## Follow container logs
	docker compose logs -f

shell: .env ## Open a Django shell
	$(RUN) python manage.py shell

migrate: .env ## Apply migrations
	$(RUN) python manage.py migrate

migrations: .env ## Create migrations after a model change
	$(RUN) python manage.py makemigrations

superuser: .env ## Create an admin user
	$(RUN) python manage.py createsuperuser

test: .env ## Run pytest against Postgres (config.settings.test)
	$(RUN) pytest

lint: .env ## ruff check and ruff format --check
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format: .env ## Fix lint issues and format the code
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

build-prod: ## Build the production image locally
	docker build -f docker/Dockerfile --target prod -t $(PROD_IMAGE) .
