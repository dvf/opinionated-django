from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from orders.dtos.order import OrderDTO
from products.dtos.product import ProductDTO


# ---- time --------------------------------------------------------------


@pytest.fixture
def frozen_time():
    """Freeze time at a deterministic instant. Use when tests care about now()."""
    with freeze_time("2026-01-01T00:00:00Z") as frozen:
        yield frozen


# ---- DTO builders ------------------------------------------------------


@pytest.fixture
def make_product_dto():
    """Build a ProductDTO with sensible defaults; override anything via kwargs."""

    def _build(**overrides: Any) -> ProductDTO:
        fields: dict[str, Any] = {
            "id": "prd_01jq3v8f6a7b2c8d9e0f1g2h3j",
            "name": "Widget",
            "price": Decimal("9.99"),
            "stock": 5,
        }
        fields.update(overrides)
        return ProductDTO(**fields)

    return _build


@pytest.fixture
def make_order_dto():
    """Build an OrderDTO with sensible defaults; override anything via kwargs."""

    def _build(**overrides: Any) -> OrderDTO:
        fields: dict[str, Any] = {
            "id": "ord_01jq3v8f6a7b2c8d9e0f1g2h3j",
            "date": datetime.now(tz=timezone.utc),
            "total": Decimal("9.99"),
            "items": [],
        }
        fields.update(overrides)
        return OrderDTO(**fields)

    return _build


# ---- repository mocks --------------------------------------------------


@pytest.fixture
def mock_product_repo(make_product_dto):
    """A MagicMock spec'd against ProductRepository, pre-loaded with a DTO."""
    from products.repositories.product import ProductRepository

    repo = MagicMock(spec=ProductRepository)
    repo.create.return_value = make_product_dto()
    repo.get_by_id.return_value = make_product_dto()
    repo.list_all.return_value = [make_product_dto()]
    repo.decrement_stock.return_value = None
    return repo


@pytest.fixture
def mock_order_repo(make_order_dto):
    """A MagicMock spec'd against OrderRepository, pre-loaded with a DTO."""
    from orders.repositories.order import OrderRepository

    repo = MagicMock(spec=OrderRepository)
    repo.create.return_value = make_order_dto()
    repo.get_by_id.return_value = make_order_dto()
    repo.list_all.return_value = [make_order_dto()]
    return repo
