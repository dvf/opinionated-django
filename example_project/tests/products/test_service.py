from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from products.dtos.product import ProductDTO
from products.repositories.product import ProductRepository
from products.services.product import ProductService


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
def mock_product_repo(make_product_dto):
    """A MagicMock spec'd against ProductRepository, pre-loaded with a DTO."""
    repo = MagicMock(spec=ProductRepository)
    repo.create.return_value = make_product_dto()
    repo.get_by_id.return_value = make_product_dto()
    repo.list_all.return_value = [make_product_dto()]
    return repo


def test_create_product_delegates_to_repo(mock_product_repo, make_product_dto):
    mock_product_repo.create.return_value = make_product_dto(name="Gadget")

    service = ProductService(mock_product_repo)
    result = service.create_product(name="Gadget", price=Decimal("9.99"), stock=5)

    assert result.name == "Gadget"
    mock_product_repo.create.assert_called_once_with(
        name="Gadget", price=Decimal("9.99"), stock=5
    )


def test_get_product_delegates_to_repo(mock_product_repo, make_product_dto):
    mock_product_repo.get_by_id.return_value = make_product_dto(id="prd_fake")

    service = ProductService(mock_product_repo)
    result = service.get_product("prd_fake")

    assert result.id == "prd_fake"
    mock_product_repo.get_by_id.assert_called_once_with("prd_fake")


def test_list_products_returns_repo_results(mock_product_repo, make_product_dto):
    expected = [
        make_product_dto(id="prd_one", name="One"),
        make_product_dto(id="prd_two", name="Two"),
    ]
    mock_product_repo.list_all.return_value = expected

    service = ProductService(mock_product_repo)
    result = service.list_products()

    assert result == expected
    mock_product_repo.list_all.assert_called_once_with()


def test_list_products_empty(mock_product_repo):
    mock_product_repo.list_all.return_value = []

    service = ProductService(mock_product_repo)
    result = service.list_products()

    assert result == []
    mock_product_repo.list_all.assert_called_once_with()
