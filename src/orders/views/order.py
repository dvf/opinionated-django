import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from project.services import get

from ..services.order import OrderService


@csrf_exempt
def order_list(request):
    service = get(OrderService)

    if request.method == "GET":
        orders = service.list_orders()
        return JsonResponse([o.model_dump(mode="json") for o in orders], safe=False)

    elif request.method == "POST":
        data = json.loads(request.body)
        try:
            order = service.create_order(items=data["items"])
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        return JsonResponse(order.model_dump(mode="json"), status=201)


@csrf_exempt
def order_detail(request, order_id):
    service = get(OrderService)

    if request.method == "GET":
        try:
            order = service.get_order(order_id)
            return JsonResponse(order.model_dump(mode="json"))
        except Exception:
            return HttpResponse(status=404)
