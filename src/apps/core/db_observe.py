"""Database observability helpers for the db_observe management command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from django.db import connection
from django.db.models import QuerySet

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

LAB_TABLES = ("catalog_product", "orders_order", "orders_orderitem")
PAGE_SIZE = 20


@dataclass(frozen=True)
class QueryScenario:
    name: str
    description: str
    builder: Callable[[], QuerySet]


def _category_list_queryset() -> QuerySet:
    return (
        Product.objects.filter(category="electronics")
        .order_by("-created_at")[:PAGE_SIZE]
    )


def _catalog_list_queryset() -> QuerySet:
    return Product.objects.order_by("-created_at")[:PAGE_SIZE]


def _product_detail_queryset() -> QuerySet:
    return Product.objects.filter(pk=1)


def _orders_by_status_queryset() -> QuerySet:
    return Order.objects.filter(status=Order.Status.PENDING).order_by("-created_at")[
        :PAGE_SIZE
    ]


def _order_items_queryset() -> QuerySet:
    return OrderItem.objects.filter(order_id=1)


SCENARIOS: dict[str, QueryScenario] = {
    "category_list": QueryScenario(
        name="category_list",
        description="Product list filtered by category (mirrors ?category=electronics)",
        builder=_category_list_queryset,
    ),
    "catalog_list": QueryScenario(
        name="catalog_list",
        description="Product list without category filter",
        builder=_catalog_list_queryset,
    ),
    "product_detail": QueryScenario(
        name="product_detail",
        description="Product lookup by primary key",
        builder=_product_detail_queryset,
    ),
    "orders_by_status": QueryScenario(
        name="orders_by_status",
        description="Orders filtered by pending status",
        builder=_orders_by_status_queryset,
    ),
    "order_items": QueryScenario(
        name="order_items",
        description="Order items for a single order",
        builder=_order_items_queryset,
    ),
}


def is_postgresql() -> bool:
    return connection.vendor == "postgresql"


def scenario_sql(scenario: QueryScenario) -> tuple[str, tuple]:
    queryset = scenario.builder()
    return queryset.query.sql_with_params()


def scan_type(plan_lines: list[str]) -> str | None:
    for line in plan_lines:
        normalized = line.strip()
        if "Seq Scan" in normalized:
            return "Seq Scan"
        if "Index Scan" in normalized or "Index Only Scan" in normalized:
            return "Index Scan"
    return None
