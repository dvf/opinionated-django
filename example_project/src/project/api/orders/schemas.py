from typing import List

from ninja import Schema


class OrderItemIn(Schema):
    product_id: str
    quantity: int


class CreateOrderIn(Schema):
    items: List[OrderItemIn]
