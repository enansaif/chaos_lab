from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderCreateSerializer(serializers.Serializer):
    items = OrderItemInputSerializer(many=True, min_length=1)

    def validate_items(self, value):
        product_ids = [item["product_id"] for item in value]
        products = Product.objects.in_bulk(product_ids)
        missing = set(product_ids) - set(products.keys())
        if missing:
            raise serializers.ValidationError(
                f"Products not found: {sorted(missing)}"
            )
        for item in value:
            item["_product"] = products[item["product_id"]]
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id")
    product_name = serializers.CharField(source="product.name")

    class Meta:
        model = OrderItem
        fields = ["product_id", "product_name", "quantity", "unit_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total", "items", "created_at", "updated_at"]


def create_order_from_items(items_data):
    order = Order.objects.create(status=Order.Status.PROCESSING)
    total = Decimal("0.00")
    order_items = []

    for item in items_data:
        product = item["_product"]
        quantity = item["quantity"]
        line_total = product.price * quantity
        total += line_total
        order_items.append(
            OrderItem(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.price,
            )
        )

    OrderItem.objects.bulk_create(order_items)
    order.total = total
    order.status = Order.Status.COMPLETED
    order.save(update_fields=["total", "status", "updated_at"])
    return order
