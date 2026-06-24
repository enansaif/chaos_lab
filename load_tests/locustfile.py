import os
import random

from locust import HttpUser, between, task


def random_product_ids(count=3, max_id=1000):
    return [random.randint(1, max_id) for _ in range(count)]


def order_payload(product_ids=None):
    if not product_ids:
        product_ids = random_product_ids(2)
    return {
        "items": [
            {"product_id": pid, "quantity": random.randint(1, 3)}
            for pid in product_ids
        ]
    }


class CatalogReader(HttpUser):
    wait_time = between(0.1, 0.5)
    weight = 3

    @task(9)
    def list_products(self):
        category = random.choice(["electronics", "books", "clothing", "home", "sports", ""])
        params = {"page": random.randint(1, 50)}
        if category:
            params["category"] = category
        self.client.get("/api/v1/catalog/products/", params=params, name="/catalog/products/")

    @task(1)
    def product_detail(self):
        product_id = random.randint(1, int(os.getenv("SEED_PRODUCT_COUNT", "10000")))
        self.client.get(f"/api/v1/catalog/products/{product_id}/", name="/catalog/products/{id}/")


class OrderWriter(HttpUser):
    wait_time = between(0.2, 1.0)
    weight = 1

    @task
    def create_sync_order(self):
        self.client.post(
            "/api/v1/orders/",
            json=order_payload(),
            name="/orders/ [sync]",
        )


class AsyncOrderWriter(HttpUser):
    wait_time = between(0.2, 1.0)
    weight = 1

    @task(3)
    def create_async_order(self):
        with self.client.post(
            "/api/v1/orders/async/",
            json=order_payload(),
            name="/orders/async/",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"Expected 202, got {response.status_code}")
                return
            task_id = response.json().get("task_id")
            if task_id:
                self.client.get(
                    f"/api/v1/orders/tasks/{task_id}/",
                    name="/orders/tasks/{id}/",
                )


class MixedTraffic(HttpUser):
    wait_time = between(0.1, 0.8)
    weight = 5

    @task(6)
    def list_products(self):
        CatalogReader.list_products(self)

    @task(1)
    def product_detail(self):
        CatalogReader.product_detail(self)

    @task(2)
    def create_sync_order(self):
        OrderWriter.create_sync_order(self)

    @task(1)
    def create_async_order(self):
        AsyncOrderWriter.create_async_order(self)
