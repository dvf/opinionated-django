from decimal import Decimal
from typing import List

from django.db import models

from ..dtos.product import ProductDTO
from ..models.product import Product


class ProductRepository:
    def create(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        product = Product.objects.create(name=name, price=price, stock=stock)
        return ProductDTO.model_validate(product)

    def get_by_id(self, product_id: str) -> ProductDTO:
        product = Product.objects.get(id=product_id)
        return ProductDTO.model_validate(product)

    def list_all(self) -> List[ProductDTO]:
        products = Product.objects.all()
        return [ProductDTO.model_validate(p) for p in products]

    def decrement_stock(self, product_id: str, quantity: int) -> None:
        updated = Product.objects.filter(id=product_id, stock__gte=quantity).update(
            stock=models.F("stock") - quantity
        )
        if not updated:
            raise ValueError(f"Insufficient stock for product {product_id}")
