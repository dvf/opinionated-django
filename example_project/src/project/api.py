from decimal import Decimal
from typing import List

from ninja import NinjaAPI, Router, Schema, Status

from example_project.src.orders.dtos.order import OrderDTO
from example_project.src.orders.services.order import OrderService
from example_project.src.products.dtos.product import ProductDTO
from example_project.src.products.services.product import ProductService
from example_project.src.project.services import get

api = NinjaAPI()

# --- Products ---

products_router = Router()


class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int


@products_router.get("/", response=List[ProductDTO])
def list_products(request):
    service = get(ProductService)
    return service.list_products()


@products_router.post("/", response={201: ProductDTO})
def create_product(request, payload: CreateProductIn):
    service = get(ProductService)
    return Status(
        201,
        service.create_product(
            name=payload.name, price=payload.price, stock=payload.stock
        ),
    )


@products_router.get("/{product_id}/", response=ProductDTO)
def get_product(request, product_id: str):
    service = get(ProductService)
    return service.get_product(product_id)


# --- Orders ---

orders_router = Router()


class OrderItemIn(Schema):
    product_id: str
    quantity: int


class CreateOrderIn(Schema):
    items: List[OrderItemIn]


@orders_router.get("/", response=List[OrderDTO])
def list_orders(request):
    service = get(OrderService)
    return service.list_orders()


@orders_router.post("/", response={201: OrderDTO})
def create_order(request, payload: CreateOrderIn):
    service = get(OrderService)
    items = [item.model_dump() for item in payload.items]
    return Status(201, service.create_order(items=items))


@orders_router.get("/{order_id}/", response=OrderDTO)
def get_order(request, order_id: str):
    service = get(OrderService)
    return service.get_order(order_id)


api.add_router("/products", products_router)
api.add_router("/orders", orders_router)
