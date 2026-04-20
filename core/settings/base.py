import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from typing import Any

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY:str = os.environ.get("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
]

LOCAL_APPS = [
    "core.apps.CoreConfig",
    "accounts",
    "audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestIDMiddleware",
    "core.middleware.RequestLoggingMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),
        "PORT": os.environ.get("POSTGRES_PORT"),
    }
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ALWAYS_EAGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_LIFETIME_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_LIFETIME_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TSES Assessment API",
    "DESCRIPTION": "TSES Assessment API that handles email-based OTP authentication with Redis rate limiting, Celery async tasks, and JWT tokens.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "OTP request and verification endpoints"},
        {"name": "audit", "description": "Audit log endpoints"},
        {"name": "health", "description": "Health and readiness checks"},
    ],
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "auth.User"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.logging_formatters.JSONFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", "300"))  # 5 min
OTP_MAX_REQUESTS_PER_EMAIL = int(os.environ.get("OTP_MAX_REQUESTS_PER_EMAIL", "3"))
OTP_EMAIL_WINDOW_SECONDS = int(os.environ.get("OTP_EMAIL_WINDOW_SECONDS", "600"))  # 10 min
OTP_MAX_REQUESTS_PER_IP = int(os.environ.get("OTP_MAX_REQUESTS_PER_IP", "10"))
OTP_IP_WINDOW_SECONDS = int(os.environ.get("OTP_IP_WINDOW_SECONDS", "3600"))  # 1 hour
OTP_MAX_FAILED_ATTEMPTS = int(os.environ.get("OTP_MAX_FAILED_ATTEMPTS", "5"))
OTP_LOCKOUT_WINDOW_SECONDS = int(os.environ.get("OTP_LOCKOUT_WINDOW_SECONDS", "900"))  # 15 min
GLOBAL_RATE_LIMIT_PER_IP = int(os.environ.get("GLOBAL_RATE_LIMIT_PER_IP", "100"))
GLOBAL_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("GLOBAL_RATE_LIMIT_WINDOW_SECONDS", "60"))
