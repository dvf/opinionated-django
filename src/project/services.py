import svcs
from products.repositories.product import ProductRepository
from products.services.product import ProductService
from orders.repositories.order import OrderRepository
from orders.services.order import OrderService

# Global registry for services
registry = svcs.Registry()

# Register Repositories
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)


# Register Services (factories pull repos from the container)
def _product_service_factory(container: svcs.Container) -> ProductService:
    repo = container.get(ProductRepository)
    return ProductService(repo)


def _order_service_factory(container: svcs.Container) -> OrderService:
    repo = container.get(OrderRepository)
    product_repo = container.get(ProductRepository)
    return OrderService(repo, product_repo)


registry.register_factory(ProductService, _product_service_factory)
registry.register_factory(OrderService, _order_service_factory)


def get[T](service_type: type[T]) -> T:
    """Get a service from the registry. Works anywhere — views, tasks, commands."""
    return svcs.Container(registry).get(service_type)
