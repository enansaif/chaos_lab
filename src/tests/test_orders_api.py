import pytest


@pytest.mark.django_db
def test_create_order_sync(api_client, product):
    response = api_client.post(
        "/api/v1/orders/",
        {"items": [{"product_id": product.id, "quantity": 2}]},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["total"] == "59.98"
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == product.id
    assert body["items"][0]["product_name"] == product.name
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["unit_price"] == "29.99"


@pytest.mark.django_db
def test_create_order_multiple_items(api_client, products):
    response = api_client.post(
        "/api/v1/orders/",
        {
            "items": [
                {"product_id": products[0].id, "quantity": 1},
                {"product_id": products[1].id, "quantity": 3},
            ]
        },
        format="json",
    )

    assert response.status_code == 201
    assert len(response.json()["items"]) == 2


@pytest.mark.django_db
def test_create_order_missing_product(api_client):
    response = api_client.post(
        "/api/v1/orders/",
        {"items": [{"product_id": 9999, "quantity": 1}]},
        format="json",
    )

    assert response.status_code == 400
    assert "Products not found" in str(response.json())


@pytest.mark.django_db
def test_create_order_empty_items(api_client):
    response = api_client.post("/api/v1/orders/", {"items": []}, format="json")

    assert response.status_code == 400


@pytest.mark.django_db
def test_order_detail(api_client, product):
    create_response = api_client.post(
        "/api/v1/orders/",
        {"items": [{"product_id": product.id, "quantity": 1}]},
        format="json",
    )
    order_id = create_response.json()["id"]

    response = api_client.get(f"/api/v1/orders/{order_id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == order_id
    assert body["items"][0]["product_id"] == product.id


@pytest.mark.django_db
def test_order_detail_not_found(api_client):
    response = api_client.get("/api/v1/orders/9999/")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


@pytest.mark.django_db
def test_create_order_async(api_client, product):
    response = api_client.post(
        "/api/v1/orders/async/",
        {"items": [{"product_id": product.id, "quantity": 1}]},
        format="json",
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["task_id"]


@pytest.mark.django_db
def test_task_status_after_async_order(api_client, product):
    create_response = api_client.post(
        "/api/v1/orders/async/",
        {"items": [{"product_id": product.id, "quantity": 2}]},
        format="json",
    )
    task_id = create_response.json()["task_id"]

    status_response = api_client.get(f"/api/v1/orders/tasks/{task_id}/")

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "SUCCESS"
    assert body["ready"] is True
    assert body["result"]["status"] == "completed"
    assert body["result"]["total"] == "59.98"
