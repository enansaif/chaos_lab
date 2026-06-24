from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class SystemConfigView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "cache_enabled": settings.CACHE_ENABLED,
                "cache_ttl_seconds": settings.CACHE_TTL_SECONDS,
                "cache_backend": (
                    "redis" if settings.CACHE_ENABLED else "dummy"
                ),
                "celery_broker_backend": settings.CELERY_BROKER_BACKEND,
                "celery_result_backend": settings.CELERY_RESULT_BACKEND,
                "uvicorn_workers": settings.UVICORN_WORKERS,
                "celery_concurrency": settings.CELERY_CONCURRENCY,
                "database_conn_max_age": settings.DATABASES["default"]["CONN_MAX_AGE"],
                "celery_task_sleep_seconds": settings.CELERY_TASK_SLEEP_SECONDS,
                "slow_request_ms": settings.SLOW_REQUEST_MS,
                "otel_enabled": settings.OTEL_ENABLED,
                "otel_service_name": settings.OTEL_SERVICE_NAME,
                "otel_exporter_endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                "otel_traces_sampler_arg": settings.OTEL_TRACES_SAMPLER_ARG,
            }
        )
