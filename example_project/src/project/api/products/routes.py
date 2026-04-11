from typing import List

from ninja import Router, Status

from products.dtos.product import ProductDTO
from products.services.product import ProductService
from project.services import get
from project.types import AuthedRequest

from .schemas import CreateProductIn

router = Router()


@router.get("/", response=List[ProductDTO])
def list_products(request: AuthedRequest):
    return get(ProductService).list_products()


@router.post("/", response={201: ProductDTO})
def create_product(request: AuthedRequest, payload: CreateProductIn):
    dto = get(ProductService).create_product(
        name=payload.name, price=payload.price, stock=payload.stock,
    )
    return Status(201, dto)


@router.get("/{product_id}/", response=ProductDTO)
def get_product(request: AuthedRequest, product_id: str):
    return get(ProductService).get_product(product_id)
