import factory

from apps.catalog.models import Product


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:08d}")
    price = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    category = factory.Iterator(["electronics", "books", "clothing", "home", "sports"])
    description = factory.Faker("sentence")
