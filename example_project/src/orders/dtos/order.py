from datetime import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


class OrderItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    order_id: str
    quantity: int
    price_at_purchase: Decimal


class OrderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: datetime
    total: Decimal
    items: List[OrderItemDTO] = []

    @field_validator("items", mode="before")
    @classmethod
    def coerce_related_manager(cls, v):
        if hasattr(v, "all"):
            return list(v.all())
        return v
