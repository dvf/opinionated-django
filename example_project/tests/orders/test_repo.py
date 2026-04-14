from decimal import Decimal

import pytest

from orders.repositories.order import OrderRepository
from products.repositories.product import ProductRepository


@pytest.mark.django_db
def test_create_order_repo():
    """
    Test that OrderRepository creates an order and items.
    """
    product_repo = ProductRepository()
    product = product_repo.create(name="P1", price=Decimal("10.00"), stock=100)

    order_repo = OrderRepository()
    items_data = [{"product_id": product.id, "quantity": 3}]
    order_dto = order_repo.create(items=items_data)

    assert order_dto.id.startswith("ord_")
    assert order_dto.total == Decimal("30.00")
    assert len(order_dto.items) == 1
    assert order_dto.items[0].id.startswith("itm_")
    assert order_dto.items[0].product_id == product.id
    assert order_dto.items[0].price_at_purchase == Decimal("10.00")


@pytest.mark.django_db
def test_get_by_id_round_trips():
    """
    Test that an order created via the repo can be fetched back by id.
    """
    product_repo = ProductRepository()
    product = product_repo.create(name="P1", price=Decimal("10.00"), stock=100)

    order_repo = OrderRepository()
    created = order_repo.create(items=[{"product_id": product.id, "quantity": 2}])

    fetched = order_repo.get_by_id(created.id)

    assert fetched == created
