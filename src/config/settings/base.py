import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    CACHE_ENABLED=(bool, True),
    DATABASE_CONN_MAX_AGE=(int, 60),
    CACHE_TTL_SECONDS=(int, 60),
    CELERY_TASK_SLEEP_SECONDS=(float, 0.5),
    SLOW_REQUEST_MS=(int, 500),
    UVICORN_WORKERS=(int, 4),
    CELERY_CONCURRENCY=(int, 4),
    SEED_PRODUCT_COUNT=(int, 10000),
    OTEL_ENABLED=(bool, True),
    OTEL_TRACES_SAMPLER_ARG=(float, 1.0),
)

environ.Env.read_env(os.path.join(BASE_DIR.parent, ".env"))

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "apps.core",
    "apps.catalog",
    "apps.orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestTimingMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Load Lab API",
    "DESCRIPTION": "Distributed systems optimization learning lab",
    "VERSION": "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

# Runtime toggles exposed to views
CACHE_ENABLED = env("CACHE_ENABLED")
CACHE_TTL_SECONDS = env("CACHE_TTL_SECONDS")
CELERY_BROKER_BACKEND = env("CELERY_BROKER_BACKEND", default="redis")
CELERY_TASK_SLEEP_SECONDS = env("CELERY_TASK_SLEEP_SECONDS")
SLOW_REQUEST_MS = env("SLOW_REQUEST_MS")
UVICORN_WORKERS = env("UVICORN_WORKERS")
CELERY_CONCURRENCY = env("CELERY_CONCURRENCY")
SEED_PRODUCT_COUNT = env("SEED_PRODUCT_COUNT")

OTEL_ENABLED = env("OTEL_ENABLED")
OTEL_EXPORTER_OTLP_ENDPOINT = env(
    "OTEL_EXPORTER_OTLP_ENDPOINT", default="http://otel-collector:4317"
)
OTEL_SERVICE_NAME = env("OTEL_SERVICE_NAME", default="loadlab-api")
OTEL_TRACES_SAMPLER_ARG = env("OTEL_TRACES_SAMPLER_ARG")

from config.settings.database import *  # noqa: E402, F403
from config.settings.cache import *  # noqa: E402, F403
from config.settings.celery_settings import *  # noqa: E402, F403
from config.settings.logging import *  # noqa: E402, F403
