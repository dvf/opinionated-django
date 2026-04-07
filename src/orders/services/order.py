from typing import Any, Dict, List

from ..dtos.order import OrderDTO
from ..repositories.order import OrderRepository
from products.repositories.product import ProductRepository


class OrderService:
    def __init__(self, repo: OrderRepository, product_repo: ProductRepository):
        self.repo = repo
        self.product_repo = product_repo

    def create_order(self, items: List[Dict[str, Any]]) -> OrderDTO:
        for item in items:
            product = self.product_repo.get_by_id(item["product_id"])
            if product.stock < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for product {product.name}: "
                    f"requested {item['quantity']}, available {product.stock}"
                )

        order = self.repo.create(items=items)

        for item in items:
            self.product_repo.decrement_stock(item["product_id"], item["quantity"])

        return order

    def get_order(self, order_id: str) -> OrderDTO:
        return self.repo.get_by_id(order_id)

    def list_orders(self) -> List[OrderDTO]:
        return self.repo.list_all()
