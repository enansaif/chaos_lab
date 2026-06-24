from config.settings.base import env

CELERY_BROKER_BACKEND = env("CELERY_BROKER_BACKEND", default="redis")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default="redis://redis:6379/2"
)

_broker_backend = CELERY_BROKER_BACKEND.lower()
if _broker_backend == "redis":
    CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
elif _broker_backend == "rabbitmq":
    CELERY_BROKER_URL = env(
        "RABBITMQ_URL", default="amqp://guest:guest@rabbitmq:5672//"
    )
else:
    raise ValueError(
        f"Invalid CELERY_BROKER_BACKEND: {CELERY_BROKER_BACKEND}. "
        "Use 'redis' or 'rabbitmq'."
    )

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_EXTENDED = True

CELERY_BEAT_SCHEDULE = {
    "warm-catalog-cache": {
        "task": "apps.orders.tasks.warm_catalog_cache",
        "schedule": 300.0,
    },
}
