from django.core.management.base import BaseCommand

from apps.catalog.models import Product


CATEGORIES = ["electronics", "books", "clothing", "home", "sports"]


class Command(BaseCommand):
    help = "Seed catalog with sample products for load testing"

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
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing products.")

        existing = Product.objects.count()
        if existing >= count:
            self.stdout.write(
                self.style.WARNING(
                    f"Already have {existing} products (target {count}). "
                    "Use --flush to recreate."
                )
            )
            return

        to_create = count - existing
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
