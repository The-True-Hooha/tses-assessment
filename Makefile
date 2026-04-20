APP=core
MANAGE=uv run python manage.py

# getting started
install:
	uv sync

export:
	uv export --format requirements-txt > requirements.txt

# django management
run:
	$(MANAGE) runserver

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

health-check:
	$(MANAGE) check

shell:
	$(MANAGE) shell

superuser:
	$(MANAGE) createsuperuser

collectstatic:
	$(MANAGE) collectstatic --noinput

# celery
worker:
	uv run celery -A $(APP) worker -l info

beat:
	uv run celery -A $(APP) beat -l info

# run tests
test:
	uv run pytest

lint:
	uv run black .
	uv run isort .

# docker
build:
	docker compose up --build

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

# help
help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies with uv"
	@echo "  make export         - Export requirements.txt"
	@echo "  make run            - Run Django dev server"
	@echo "  make migrate        - Apply migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make shell          - Django shell"
	@echo "  make superuser      - Create superuser"
	@echo "  make worker         - Run Celery worker"
	@echo "  make beat           - Run Celery beat"
	@echo "  make build          - Build and start Docker"
	@echo "  make up             - Start Docker"
	@echo "  make down           - Stop Docker"
	@echo "  make logs           - View Docker logs"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Format code"
