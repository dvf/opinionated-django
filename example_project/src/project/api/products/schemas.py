from decimal import Decimal

from ninja import Schema


class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int
