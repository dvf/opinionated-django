from decimal import Decimal
from typing import List

from ninja import NinjaAPI, Router, Schema, Status

from project.types import ServiceRequest

from orders.dtos.order import OrderDTO
from orders.repositories.order import OrderRepository
from orders.services.order import OrderService
from products.dtos.product import ProductDTO
from products.repositories.product import ProductRepository
from products.services.product import ProductService

api = NinjaAPI()

# --- Products ---

products_router = Router()


class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int


@products_router.get("/", response=List[ProductDTO])
def list_products(request: ServiceRequest):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return service.list_products()


@products_router.post("/", response={201: ProductDTO})
def create_product(request: ServiceRequest, payload: CreateProductIn):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return Status(
        201,
        service.create_product(
            name=payload.name, price=payload.price, stock=payload.stock
        ),
    )


@products_router.get("/{product_id}/", response=ProductDTO)
def get_product(request: ServiceRequest, product_id: str):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return service.get_product(product_id)


# --- Orders ---

orders_router = Router()


class OrderItemIn(Schema):
    product_id: str
    quantity: int


class CreateOrderIn(Schema):
    items: List[OrderItemIn]


@orders_router.get("/", response=List[OrderDTO])
def list_orders(request: ServiceRequest):
    repo = request.services.get(OrderRepository)
    product_repo = request.services.get(ProductRepository)
    service = OrderService(repo, product_repo)
    return service.list_orders()


@orders_router.post("/", response={201: OrderDTO})
def create_order(request: ServiceRequest, payload: CreateOrderIn):
    repo = request.services.get(OrderRepository)
    product_repo = request.services.get(ProductRepository)
    service = OrderService(repo, product_repo)
    items = [item.model_dump() for item in payload.items]
    return Status(201, service.create_order(items=items))


@orders_router.get("/{order_id}/", response=OrderDTO)
def get_order(request: ServiceRequest, order_id: str):
    repo = request.services.get(OrderRepository)
    product_repo = request.services.get(ProductRepository)
    service = OrderService(repo, product_repo)
    return service.get_order(order_id)


api.add_router("/products", products_router)
api.add_router("/orders", orders_router)
