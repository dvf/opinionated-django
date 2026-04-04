import svcs
from django.http import HttpRequest

__all__ = ["ServiceRequest"]


class ServiceRequest(HttpRequest):
    """HttpRequest with a svcs.Container attached by SvcsMiddleware."""

    services: svcs.Container
