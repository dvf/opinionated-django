import svcs

from project.services import get, registry


class TestServicesGet:
    def test_get_returns_registered_service(self):
        """Verify get() resolves a registered type from the registry."""
        from products.services.product import ProductService

        service = get(ProductService)
        assert isinstance(service, ProductService)

    def test_get_wires_dependencies(self):
        """Verify service factories receive their repo dependencies."""
        from orders.services.order import OrderService

        service = get(OrderService)
        assert isinstance(service, OrderService)
        assert service.repo is not None
        assert service.product_repo is not None

    def test_registry_is_svcs_registry(self):
        assert isinstance(registry, svcs.Registry)
