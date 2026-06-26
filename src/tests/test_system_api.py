import pytest
from django.conf import settings


@pytest.mark.django_db
def test_system_config(api_client):
    response = api_client.get("/api/v1/system/config/")

    assert response.status_code == 200
    body = response.json()
    assert body["cache_enabled"] == settings.CACHE_ENABLED
    assert body["cache_ttl_seconds"] == settings.CACHE_TTL_SECONDS
    assert body["cache_backend"] == "dummy"
    assert body["celery_broker_backend"] == settings.CELERY_BROKER_BACKEND
    assert body["uvicorn_workers"] == settings.UVICORN_WORKERS
    assert body["otel_enabled"] is False
