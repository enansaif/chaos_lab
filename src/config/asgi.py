import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.telemetry import init_telemetry

init_telemetry(
    os.environ.get("OTEL_SERVICE_NAME", "loadlab-api"),
    instrument_django=True,
)

from django.core.asgi import get_asgi_application

application = get_asgi_application()
