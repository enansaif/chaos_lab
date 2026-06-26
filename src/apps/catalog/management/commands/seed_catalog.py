from django.core.management.base import BaseCommand
from django.db import connection

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


CATEGORIES = ["electronics", "books", "clothing", "home", "sports"]


class Command(BaseCommand):
    help = "Seed catalog with sample products for load testing"

    def _truncate_catalog_and_orders(self):
        tables = ", ".join(
            connection.ops.quote_name(model._meta.db_table)
            for model in (OrderItem, Order, Product)
        )
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=None,
            help="Number of products to create",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing products before seeding",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        count = options["count"] or settings.SEED_PRODUCT_COUNT

        if options["flush"]:
            order_count = Order.objects.count()
            product_count = Product.objects.count()
            self._truncate_catalog_and_orders()
            self.stdout.write(
                f"Truncated {product_count} products, {order_count} orders, "
                "and reset primary key sequences."
            )

        existing = Product.objects.count()
        if existing >= count:
            self.stdout.write(
                self.style.WARNING(
                    f"Already have {existing} products (target {count}). "
                    "Use --flush to recreate."
                )
            )
            return

        batch_size = 1000
        products = []

        for i in range(existing, count):
            category = CATEGORIES[i % len(CATEGORIES)]
            products.append(
                Product(
                    name=f"Product {i + 1}",
                    sku=f"SKU-{i + 1:08d}",
                    price=round(9.99 + (i % 500) * 0.1, 2),
                    category=category,
                    description=f"Sample product {i + 1} in {category}",
                )
            )

            if len(products) >= batch_size:
                Product.objects.bulk_create(products, ignore_conflicts=True)
                products = []
                self.stdout.write(f"Created {min(i + 1, count)}/{count}...")

        if products:
            Product.objects.bulk_create(products, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(f"Seeded catalog with {Product.objects.count()} products.")
        )
