import pytest


@pytest.mark.django_db
def test_health_live(api_client):
    response = api_client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.django_db
def test_health_ready(api_client):
    response = api_client.get("/health/ready/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["cache"]["ok"] is True
    assert body["checks"]["celery_broker"]["ok"] is True
