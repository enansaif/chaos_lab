import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("apps.core.health")


@require_GET
def live(request):
    return JsonResponse({"status": "alive"})


@require_GET
def ready(request):
    checks = {}
    overall_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {"ok": True}
    except Exception as exc:
        checks["database"] = {"ok": False, "error": str(exc)}
        overall_ok = False

    if settings.CACHE_ENABLED:
        try:
            cache.set("health_check", "ok", timeout=5)
            value = cache.get("health_check")
            if value != "ok":
                raise ValueError("Cache read/write mismatch")
            checks["cache"] = {"ok": True, "backend": "redis"}
        except Exception as exc:
            checks["cache"] = {"ok": False, "error": str(exc)}
            overall_ok = False
    else:
        checks["cache"] = {"ok": True, "backend": "dummy", "enabled": False}

    try:
        from config.celery import app as celery_app

        conn = celery_app.connection()
        conn.ensure_connection(max_retries=1)
        conn.release()
        checks["celery_broker"] = {
            "ok": True,
            "backend": settings.CELERY_BROKER_BACKEND,
        }
    except Exception as exc:
        checks["celery_broker"] = {
            "ok": False,
            "backend": settings.CELERY_BROKER_BACKEND,
            "error": str(exc),
        }
        overall_ok = False

    status_code = 200 if overall_ok else 503
    return JsonResponse(
        {"status": "ready" if overall_ok else "not_ready", "checks": checks},
        status=status_code,
    )
