import json
from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from project.types import ServiceRequest

from ..repositories.product import ProductRepository
from ..services.product import ProductService


@csrf_exempt
def product_list(request: ServiceRequest):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)

    if request.method == "GET":
        products = service.list_products()
        return JsonResponse([p.model_dump() for p in products], safe=False)

    elif request.method == "POST":
        data = json.loads(request.body)
        product = service.create_product(
            name=data["name"], price=Decimal(data["price"]), stock=data["stock"]
        )
        return JsonResponse(product.model_dump(), status=201)


@csrf_exempt
def product_detail(request: ServiceRequest, product_id):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)

    if request.method == "GET":
        try:
            product = service.get_product(product_id)
            return JsonResponse(product.model_dump())
        except Exception:
            return HttpResponse(status=404)
