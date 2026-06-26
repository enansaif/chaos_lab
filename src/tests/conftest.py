import os

# Set before Django/Celery imports so telemetry and brokers stay test-local.
os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
os.environ["OTEL_ENABLED"] = "false"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["CELERY_BROKER_BACKEND"] = "memory"

import pytest
from rest_framework.test import APIClient

from tests.factories import ProductFactory


def pytest_configure():
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    os.environ["OTEL_ENABLED"] = "false"
    os.environ["CELERY_BROKER_URL"] = "memory://"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
    os.environ["CELERY_BROKER_BACKEND"] = "memory"


def pytest_sessionfinish(session, exitstatus):
    from config.telemetry import shutdown_telemetry

    shutdown_telemetry()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def product(db):
    return ProductFactory(
        name="Test Widget",
        sku="SKU-TEST-001",
        price="29.99",
        category="electronics",
    )


@pytest.fixture
def products(db):
    return ProductFactory.create_batch(3)
