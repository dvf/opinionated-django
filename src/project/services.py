import svcs
from products.repositories.product import ProductRepository
from orders.repositories.order import OrderRepository

# Global registry for services
registry = svcs.Registry()

# Register Repositories
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)
