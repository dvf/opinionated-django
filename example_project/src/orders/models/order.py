from typing import ClassVar

from django.db import models

from products.models.product import Product
from project.ids import generate_itm_id, generate_ord_id


class Order(models.Model):
    class Meta:
        verbose_name = "order"
        verbose_name_plural = "orders"
        indexes = [
            models.Index(fields=["-date"], name="idx_%(class)s_recent"),
        ]

    __prefix__: ClassVar[str] = "ord"

    id = models.CharField(
        max_length=64, primary_key=True, default=generate_ord_id, editable=False
    )
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Order {self.id} on {self.date}"


class OrderItem(models.Model):
    class Meta:
        verbose_name = "order item"
        verbose_name_plural = "order items"
        indexes = [
            models.Index(fields=["order", "product"], name="idx_%(class)s_ord_prd"),
        ]

    __prefix__: ClassVar[str] = "itm"

    # Identifiers
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_itm_id, editable=False
    )

    # Domain
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(
        verbose_name="price at purchase",
        max_digits=10,
        decimal_places=2,
    )

    # Relations (always last)
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name} (Order {self.order_id})"  # type: ignore[attr-defined]
