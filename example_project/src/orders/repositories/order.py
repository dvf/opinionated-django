from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction

from products.models.product import Product

from ..dtos.order import OrderDTO
from ..models.order import Order, OrderItem


class OrderRepository:
    @transaction.atomic
    def create(self, items: List[Dict[str, Any]]) -> OrderDTO:
        total = Decimal("0.00")
        order = Order.objects.create(total=total)

        for item_data in items:
            product = Product.objects.get(id=item_data["product_id"])
            price = product.price
            quantity = item_data["quantity"]
            total += price * quantity

            OrderItem.objects.create(
                order=order, product=product, quantity=quantity, price_at_purchase=price
            )

        order.total = total
        order.save()

        order_with_items = Order.objects.prefetch_related("items").get(id=order.id)
        return OrderDTO.model_validate(order_with_items)

    def get_by_id(self, order_id: str) -> OrderDTO:
        order = Order.objects.prefetch_related("items").get(id=order_id)
        return OrderDTO.model_validate(order)

    def list_all(self) -> List[OrderDTO]:
        orders = Order.objects.prefetch_related("items").all()
        return [OrderDTO.model_validate(o) for o in orders]
