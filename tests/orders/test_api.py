import pytest


@pytest.mark.django_db
def test_create_order(client):
    """
    Test that POST /orders/ creates a new order.
    """
    # First create a product to order
    product_data = {"name": "Orderable Product", "price": "50.00", "stock": 10}
    product_response = client.post(
        "/products/", data=product_data, content_type="application/json"
    )
    product_id = product_response.json()["id"]

    # Place order
    order_url = "/orders/"
    order_data = {"items": [{"product_id": product_id, "quantity": 2}]}
    response = client.post(order_url, data=order_data, content_type="application/json")

    assert response.status_code == 201
    order_json = response.json()
    assert order_json["id"].startswith("ord_")
    assert order_json["total"] == "100.00"  # 2 * 50.00
    assert len(order_json["items"]) == 1
    assert order_json["items"][0]["product_id"] == product_id
    assert order_json["items"][0]["quantity"] == 2
