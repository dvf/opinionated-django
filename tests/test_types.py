import svcs
from django.http import HttpRequest

from project.types import ServiceRequest


class TestServiceRequest:
    def test_inherits_from_http_request(self):
        assert issubclass(ServiceRequest, HttpRequest)

    def test_services_attribute_annotated_as_container(self):
        hints = ServiceRequest.__annotations__
        assert "services" in hints
        assert hints["services"] is svcs.Container

    def test_importable_from_core_types(self):
        """Verify ServiceRequest is discoverable via standard import."""
        from project.types import ServiceRequest as SR

        assert SR is ServiceRequest

    def test_svcs_container_resolvable(self):
        """Verify svcs.Container type is available (dependency chain works)."""
        assert hasattr(svcs, "Container")
        assert svcs.Container is not None


class TestMiddlewareStubSync:
    def test_middleware_assigns_svcs_container(self):
        """Runtime check that middleware assigns an svcs.Container,
        mirroring the static type declared in ServiceRequest."""
        from project.middleware import SvcsMiddleware
        from project.services import registry

        captured = {}

        def fake_get_response(request):
            captured["services"] = request.services
            from django.http import HttpResponse

            return HttpResponse()

        middleware = SvcsMiddleware(fake_get_response)
        request = HttpRequest()
        middleware(request)

        assert isinstance(captured["services"], svcs.Container)
