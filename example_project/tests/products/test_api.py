import pytest


@pytest.mark.django_db
def test_list_products_empty(client):
    """
    Test that GET /products/ returns an empty list when no products exist.
    """
    url = (
        "/products/"  # We'll use hardcoded paths for now as we haven't defined urls.py
    )
    response = client.get(url)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_create_product(client):
    """
    Test that POST /products/ creates a new product and returns it.
    """
    url = "/products/"
    data = {"name": "Test Product", "price": "10.00", "stock": 100}
    response = client.post(url, data=data, content_type="application/json")

    assert response.status_code == 201
    product_data = response.json()
    assert product_data["name"] == "Test Product"
    assert "id" in product_data
    assert product_data["id"].startswith("prd_")
    assert product_data["price"] == "10.00"
    assert product_data["stock"] == 100


@pytest.mark.django_db
def test_get_product_by_id(client):
    """
    Test that GET /products/{id}/ returns the correct product.
    """
    # First create a product
    create_url = "/products/"
    create_data = {"name": "Get Me", "price": "20.00", "stock": 50}
    create_response = client.post(
        create_url, data=create_data, content_type="application/json"
    )
    product_id = create_response.json()["id"]

    # Then retrieve it
    get_url = f"/products/{product_id}/"
    response = client.get(get_url)

    assert response.status_code == 200
    assert response.json()["name"] == "Get Me"
    assert response.json()["id"] == product_id
