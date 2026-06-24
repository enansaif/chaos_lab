import time

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator

from apps.catalog.models import Product
from apps.catalog.serializers import ProductSerializer
from apps.orders.serializers import create_order_from_items


@shared_task(bind=True, name="apps.orders.tasks.process_order_async")
def process_order_async(self, items_data):
    sleep_seconds = settings.CELERY_TASK_SLEEP_SECONDS
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    normalized = []
    product_ids = [item["product_id"] for item in items_data]
    products = Product.objects.in_bulk(product_ids)

    for item in items_data:
        product = products.get(item["product_id"])
        if not product:
            raise ValueError(f"Product {item['product_id']} not found")
        normalized.append(
            {
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "_product": product,
            }
        )

    order = create_order_from_items(normalized)
    return {"order_id": order.id, "status": order.status, "total": str(order.total)}


@shared_task(name="apps.orders.tasks.warm_catalog_cache")
def warm_catalog_cache():
    if not settings.CACHE_ENABLED:
        return {"warmed": 0, "cache_enabled": False}

    queryset = Product.objects.all().order_by("-created_at")
    paginator = Paginator(queryset, settings.REST_FRAMEWORK.get("PAGE_SIZE", 20))
    warmed = 0

    for page_num in paginator.page_range[:5]:
        page = paginator.page(page_num)
        serializer = ProductSerializer(page.object_list, many=True)
        cache_key = f"catalog:warm:page:{page_num}"
        cache.set(cache_key, serializer.data, timeout=settings.CACHE_TTL_SECONDS)
        warmed += 1

    return {"warmed": warmed, "cache_enabled": True}
