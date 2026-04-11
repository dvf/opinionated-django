from typing import List

from ninja import Router, Status

from orders.dtos.order import OrderDTO
from orders.services.order import OrderService
from project.services import get
from project.types import AuthedRequest

from .schemas import CreateOrderIn

router = Router()


@router.get("/", response=List[OrderDTO])
def list_orders(request: AuthedRequest):
    return get(OrderService).list_orders()


@router.post("/", response={201: OrderDTO})
def create_order(request: AuthedRequest, payload: CreateOrderIn):
    items = [item.model_dump() for item in payload.items]
    dto = get(OrderService).create_order(items=items)
    return Status(201, dto)


@router.get("/{order_id}/", response=OrderDTO)
def get_order(request: AuthedRequest, order_id: str):
    return get(OrderService).get_order(order_id)
