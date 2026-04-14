from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from orders.dtos.order import OrderDTO, OrderItemDTO
from orders.repositories.order import OrderRepository
from orders.services.order import OrderService
from products.dtos.product import ProductDTO
from products.repositories.product import ProductRepository


def make_product_dto(**overrides: Any) -> ProductDTO:
    fields: dict[str, Any] = {
        "id": "prd_01jq3v8f6a7b2c8d9e0f1g2h3j",
        "name": "Widget",
        "price": Decimal("9.99"),
        "stock": 5,
    }
    fields.update(overrides)
    return ProductDTO(**fields)


def make_order_dto(**overrides: Any) -> OrderDTO:
    fields: dict[str, Any] = {
        "id": "ord_01jq3v8f6a7b2c8d9e0f1g2h3k",
        "date": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "total": Decimal("19.98"),
        "items": [
            OrderItemDTO(
                id="itm_01jq3v8f6a7b2c8d9e0f1g2h3l",
                product_id="prd_01jq3v8f6a7b2c8d9e0f1g2h3j",
                order_id="ord_01jq3v8f6a7b2c8d9e0f1g2h3k",
                quantity=2,
                price_at_purchase=Decimal("9.99"),
            )
        ],
    }
    fields.update(overrides)
    return OrderDTO(**fields)


def test_create_order_happy_path():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    product_repo.get_by_id.return_value = make_product_dto(stock=10)
    expected_order = make_order_dto()
    order_repo.create.return_value = expected_order

    service = OrderService(order_repo, product_repo)
    items = [{"product_id": "prd_01jq3v8f6a7b2c8d9e0f1g2h3j", "quantity": 2}]
    result = service.create_order(items=items)

    assert result is expected_order
    product_repo.get_by_id.assert_called_once_with("prd_01jq3v8f6a7b2c8d9e0f1g2h3j")
    order_repo.create.assert_called_once_with(items=items)
    product_repo.decrement_stock.assert_called_once_with(
        "prd_01jq3v8f6a7b2c8d9e0f1g2h3j", 2
    )


def test_create_order_rejects_insufficient_stock():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    product_repo.get_by_id.return_value = make_product_dto(stock=1)

    service = OrderService(order_repo, product_repo)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_order(items=[{"product_id": "prd_fake", "quantity": 5}])

    order_repo.create.assert_not_called()
    product_repo.decrement_stock.assert_not_called()


def test_create_order_decrements_stock_after_create():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    product_repo.get_by_id.side_effect = [
        make_product_dto(id="prd_a", stock=10),
        make_product_dto(id="prd_b", stock=20),
    ]
    order_repo.create.return_value = make_order_dto()

    service = OrderService(order_repo, product_repo)
    items = [
        {"product_id": "prd_a", "quantity": 3},
        {"product_id": "prd_b", "quantity": 7},
    ]
    service.create_order(items=items)

    assert product_repo.decrement_stock.call_args_list == [
        (("prd_a", 3),),
        (("prd_b", 7),),
    ]


def test_get_order_delegates_to_repo():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    expected = make_order_dto()
    order_repo.get_by_id.return_value = expected

    service = OrderService(order_repo, product_repo)
    result = service.get_order("ord_01jq3v8f6a7b2c8d9e0f1g2h3k")

    assert result is expected
    order_repo.get_by_id.assert_called_once_with("ord_01jq3v8f6a7b2c8d9e0f1g2h3k")


def test_list_orders_returns_repo_results():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    expected = [make_order_dto()]
    order_repo.list_all.return_value = expected

    service = OrderService(order_repo, product_repo)
    assert service.list_orders() is expected
    order_repo.list_all.assert_called_once_with()


def test_list_orders_empty():
    order_repo = MagicMock(spec=OrderRepository)
    product_repo = MagicMock(spec=ProductRepository)
    order_repo.list_all.return_value = []

    service = OrderService(order_repo, product_repo)
    assert service.list_orders() == []
    order_repo.list_all.assert_called_once_with()
