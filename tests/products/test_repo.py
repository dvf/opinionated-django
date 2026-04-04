import pytest
from products.repositories.product import ProductRepository
from products.dtos.product import ProductDTO
from decimal import Decimal


@pytest.mark.django_db
def test_create_and_get_product_repo():
    """
    Test that ProductRepository creates a product and retrieves it.
    """
    repo = ProductRepository()
    product_dto = repo.create(name="Repo Product", price=Decimal("15.00"), stock=30)

    assert isinstance(product_dto, ProductDTO)
    assert isinstance(product_dto.id, str)
    assert product_dto.id.startswith("prd_")
    assert product_dto.name == "Repo Product"
    assert product_dto.price == Decimal("15.00")

    # Test get by id
    fetched_dto = repo.get_by_id(product_dto.id)
    assert fetched_dto == product_dto


@pytest.mark.django_db
def test_list_all_products_repo():
    """
    Test that ProductRepository lists all products.
    """
    repo = ProductRepository()
    repo.create(name="P1", price=Decimal("10"), stock=1)
    repo.create(name="P2", price=Decimal("20"), stock=2)

    products = repo.list_all()
    assert len(products) == 2
    assert {p.name for p in products} == {"P1", "P2"}
