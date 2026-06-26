import pytest

from tests.factories import ProductFactory


@pytest.mark.django_db
def test_list_products_empty(api_client):
    response = api_client.get("/api/v1/catalog/products/")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["results"] == []


@pytest.mark.django_db
def test_list_products(api_client, products):
    response = api_client.get("/api/v1/catalog/products/")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert len(body["results"]) == 3
    assert {"id", "name", "sku", "price", "category", "description", "created_at"} <= set(
        body["results"][0]
    )


@pytest.mark.django_db
def test_list_products_filter_by_category(api_client):
    ProductFactory(category="books")
    ProductFactory(category="electronics")

    response = api_client.get("/api/v1/catalog/products/", {"category": "books"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["category"] == "books"


@pytest.mark.django_db
def test_product_detail(api_client, product):
    response = api_client.get(f"/api/v1/catalog/products/{product.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == product.id
    assert body["sku"] == "SKU-TEST-001"
    assert body["name"] == "Test Widget"


@pytest.mark.django_db
def test_product_detail_not_found(api_client):
    response = api_client.get("/api/v1/catalog/products/9999/")

    assert response.status_code == 404
