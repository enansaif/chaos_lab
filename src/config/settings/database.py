from config.settings.base import BASE_DIR, env

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="loadlab"),
        "USER": env("POSTGRES_USER", default="loadlab"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="loadlab"),
        "HOST": env("POSTGRES_HOST", default="postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": env("DATABASE_CONN_MAX_AGE"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}
