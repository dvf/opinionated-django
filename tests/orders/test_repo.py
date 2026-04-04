import pytest
from orders.repositories.order import OrderRepository
from orders.services.order import OrderService
from products.repositories.product import ProductRepository
from decimal import Decimal


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
def test_stock_validation_rejects_insufficient_stock():
    """
    Test that OrderService rejects orders when stock is insufficient.
    """
    product_repo = ProductRepository()
    product = product_repo.create(name="Limited", price=Decimal("5.00"), stock=2)

    order_repo = OrderRepository()
    service = OrderService(order_repo, product_repo)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_order(items=[{"product_id": product.id, "quantity": 10}])


@pytest.mark.django_db
def test_stock_decremented_after_order():
    """
    Test that product stock is decremented after a successful order.
    """
    product_repo = ProductRepository()
    product = product_repo.create(name="Gadget", price=Decimal("25.00"), stock=10)

    order_repo = OrderRepository()
    service = OrderService(order_repo, product_repo)
    service.create_order(items=[{"product_id": product.id, "quantity": 3}])

    updated = product_repo.get_by_id(product.id)
    assert updated.stock == 7
