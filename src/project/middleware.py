from collections.abc import Callable

import svcs
from django.http import HttpRequest, HttpResponse

from .services import registry


class SvcsMiddleware:
    """
    Middleware that initializes a svcs.Container for each request,
    attaching it to request.services and ensuring it is closed properly.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Create a request-scoped container from the global registry
        container = svcs.Container(registry)

        # Attach to request for view access
        request.services = container  # type: ignore[attr-defined]

        try:
            response = self.get_response(request)
            return response
        finally:
            # Ensure container is closed to trigger any necessary cleanup
            container.close()
