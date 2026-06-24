import logging
import time
import uuid

from django.conf import settings

from config.telemetry import get_trace_context

logger = logging.getLogger("apps.core.middleware")


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id
        start = time.perf_counter()

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Request-ID"] = request_id
        response["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        slow_threshold = getattr(settings, "SLOW_REQUEST_MS", 500)
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            **get_trace_context(),
        }

        if duration_ms >= slow_threshold:
            logger.warning("slow_request", extra=log_data)
        else:
            logger.info("request_completed", extra=log_data)

        return response
