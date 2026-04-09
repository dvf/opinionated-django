from decimal import Decimal
from typing import List

from ..dtos.product import ProductDTO
from ..repositories.product import ProductRepository


class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def create_product(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        return self.repo.create(name=name, price=price, stock=stock)

    def get_product(self, product_id: str) -> ProductDTO:
        return self.repo.get_by_id(product_id)

    def list_products(self) -> List[ProductDTO]:
        return self.repo.list_all()
