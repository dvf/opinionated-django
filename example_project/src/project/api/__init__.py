from ninja import NinjaAPI

from project.api.orders import router as orders_router
from project.api.products import router as products_router

api = NinjaAPI()

api.add_router("/products", products_router)
api.add_router("/orders", orders_router)


@api.exception_handler(ValueError)
def on_value_error(request, exc: ValueError):
    return api.create_response(request, {"detail": str(exc)}, status=400)


@api.exception_handler(LookupError)
def on_lookup_error(request, exc: LookupError):
    return api.create_response(request, {"detail": str(exc)}, status=404)


@api.exception_handler(PermissionError)
def on_permission_error(request, exc: PermissionError):
    return api.create_response(request, {"detail": str(exc)}, status=403)
