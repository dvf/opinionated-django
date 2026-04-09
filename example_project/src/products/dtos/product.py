from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price: Decimal
    stock: int
