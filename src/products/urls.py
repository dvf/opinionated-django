from django.urls import path
from .views.product import product_list, product_detail

urlpatterns = [
    path("", product_list, name="product-list"),  # type: ignore[arg-type]
    path("<str:product_id>/", product_detail, name="product-detail"),  # type: ignore[arg-type]
]
