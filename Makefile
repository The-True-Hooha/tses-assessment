APP=core
MANAGE=uv run python manage.py

# getting started
install:
	uv sync

pip-install:
	pip install -r requirements.txt

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

worker-window:
	uv run celery -A $(APP) worker -l info --pool=solo

beat:
	uv run celery -A $(APP) beat -l info

lint:
	uv run black .
	uv run isort .

# docker
build:
	docker compose up --build

build-d:
	docker compose up --build -d

up:
	docker compose up

up-d:
	docker compose up -d

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

# help
help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies with uv"
	@echo "  make pip-install    - Install dependencies with pip"
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
