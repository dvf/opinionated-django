from django.urls import path
from .views.order import order_list, order_detail

urlpatterns = [
    path("", order_list, name="order-list"),  # type: ignore[arg-type]
    path("<str:order_id>/", order_detail, name="order-detail"),  # type: ignore[arg-type]
]
