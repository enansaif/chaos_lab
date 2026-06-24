import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.telemetry import init_telemetry

init_telemetry(os.environ.get("OTEL_SERVICE_NAME", "loadlab-worker"))

from celery import Celery

app = Celery("loadlab")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
