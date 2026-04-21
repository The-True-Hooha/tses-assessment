# TSES OTP Authentication API

Email-based OTP authentication service with Redis-backed rate limiting, Celery async tasks, JWT tokens, and full OpenAPI documentation.

---

## Quick Start

```bash
cp .env.example .env
# Before running with Docker, set POSTGRES_HOST=postgres in .env (matches the container name)
docker compose up --build
```

Open Swagger UI: http://localhost:8000/api/v1/docs/

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Django secret key (required) |
| `DEBUG` | `False` | Enable debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DJANGO_SETTINGS_MODULE` | `core.settings.dev` | Settings module to load |
| `POSTGRES_DB` | `tses_db` | PostgreSQL database name |
| `POSTGRES_USER` | `tses_user` | PostgreSQL user |
| `POSTGRES_PASSWORD` | — | PostgreSQL password (required) |
| `POSTGRES_HOST` | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `JWT_ACCESS_LIFETIME_MINUTES` | `60` | JWT access token lifetime |
| `JWT_REFRESH_LIFETIME_DAYS` | `7` | JWT refresh token lifetime |
| `OTP_TTL_SECONDS` | `300` | OTP expires after N seconds (5 min) |
| `OTP_MAX_REQUESTS_PER_EMAIL` | `3` | Max OTP requests per email per window |
| `OTP_EMAIL_WINDOW_SECONDS` | `600` | Email rate limit window (10 min) |
| `OTP_MAX_REQUESTS_PER_IP` | `10` | Max OTP requests per IP per window |
| `OTP_IP_WINDOW_SECONDS` | `3600` | IP rate limit window (1 hour) |
| `OTP_MAX_FAILED_ATTEMPTS` | `5` | Failed verify attempts before lockout |
| `OTP_LOCKOUT_WINDOW_SECONDS` | `900` | Lockout duration (15 min) |
| `GLOBAL_RATE_LIMIT_PER_IP` | `100` | Global max requests per IP per window |
| `GLOBAL_RATE_LIMIT_WINDOW_SECONDS` | `60` | Global rate limit window (1 min) |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/otp/request` | None | Request a 6-digit OTP via email |
| `POST` | `/api/v1/auth/otp/verify` | None | Verify OTP, receive JWT tokens |
| `GET` | `/api/v1/audit/logs` | Bearer JWT | List audit logs with filtering |
| `GET` | `/api/v1/docs/` | None | Swagger UI |
| `GET` | `/api/v1/redoc/` | None | ReDoc UI |
| `GET` | `/api/v1/schema/` | None | Raw OpenAPI JSON schema |
| `GET` | `/health/` | None | Health check (DB + Redis) |
| `GET` | `/` | None | API index |

---

## Rate Limits

| Limit | Value |
|---|---|
| Global per IP | 100 requests / 60 seconds |
| OTP requests per email | 3 requests / 10 minutes |
| OTP requests per IP | 10 requests / 1 hour |
| Failed OTP attempts | 5 attempts / 15 minutes → lockout |

All OTP limits use atomic Redis sliding windows (Lua scripts). No race conditions under concurrent load.

---

## Architecture

```
core/           — settings, middleware, celery, logging, rate limiter, redis client
accounts/       — OTP request/verify, JWT issuance, user creation, Celery tasks
audit/          — AuditLog model, read-only paginated endpoint
```

**Request flow:**
1. Request hits Django → `RequestIDMiddleware` stamps `X-Request-ID` + `X-Correlation-ID`
2. `RequestLoggingMiddleware` sets thread-local context, logs start/end with latency
3. View runs rate limit checks via atomic Lua scripts against Redis
4. OTP generated, hashed (SHA-256), stored in Redis with 5-min TTL
5. Celery tasks enqueued (non-blocking): email send + audit log write
6. On verify: constant-time comparison, one-time delete, JWT issued via SimpleJWT

---

## Local Development (without Docker)

**With uv (recommended):**

```bash
uv sync
cp .env.example .env
# edit .env — set POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0
uv run python manage.py migrate
uv run python manage.py runserver

# In a separate terminal
uv run celery -A core worker --loglevel=info
```

**With pip (no uv required):**

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env — set POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0
python manage.py migrate
python manage.py runserver

# In a separate terminal
celery -A core worker --loglevel=info
```

> Docker users never need uv locally — it is installed inside the image automatically.

---

## Makefile Commands

```bash
make install        # Install dependencies
make run            # Run dev server
make migrate        # Apply migrations
make makemigrations # Create new migrations
make worker         # Run Celery worker
make build          # docker compose up --build
make up             # docker compose up
make down           # docker compose down
make logs           # Tail Docker logs
make test           # Run pytest
make lint           # Format with black + isort
make shell          # Django shell
make superuser      # Create superuser
```
