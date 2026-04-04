# Django Architecture: Repository + Services + Pydantic DTOs + svcs DI

This document describes the layered architecture used in this project. It is intended as a reference for LLMs generating code in projects that follow the same patterns.

## Principles

1. **Django models are thin** -- schema and persistence only, no business logic.
2. **Repositories own all data access** -- no ORM calls outside a repository.
3. **Repositories return Pydantic DTOs** -- ORM objects never leak beyond the repository boundary.
4. **Services own business logic** -- validation, calculations, cross-repo coordination.
5. **Dependencies are injected via `svcs`** -- nothing is instantiated directly in views.
6. **Views are thin** -- retrieve services from the DI container, delegate, return.
7. **Stripe-style prefixed ULID IDs** -- every model uses a `CharField` primary key of the form `<prefix>_<ulid>`.

## Layer Diagram

```
Request
  │
  ▼
View / API endpoint  (django-ninja router)
  │  gets repos from request.services (svcs container)
  │  constructs service with repos
  ▼
Service
  │  business logic, validation, orchestration
  │  calls one or more repositories
  ▼
Repository
  │  Django ORM queries
  │  converts ORM objects → Pydantic DTOs via model_validate()
  ▼
Django Model  (thin -- schema definition only)
```

## App Structure

Each Django app follows this layout:

```
src/<app_name>/
├── dtos/
│   └── <entity>.py     # Pydantic models (output DTOs)
├── models/
│   └── <entity>.py     # Django ORM models (thin)
├── repositories/
│   └── <entity>.py     # Data access, returns DTOs
├── services/
│   └── <entity>.py     # Business logic
├── admin.py
├── apps.py
└── __init__.py
```

The central API and project config live in `project/`:

```python
# src/project/api.py
from ninja import NinjaAPI

api = NinjaAPI()
# Routers and endpoints defined here
api.add_router("/products", products_router)
api.add_router("/orders", orders_router)
```

And mounted in `project/urls.py`:

```python
from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]
```

## ID Strategy

All models use **Stripe-style prefixed ULID** primary keys. IDs are strings of the form `<prefix>_<lowercase_ulid>`, e.g. `prd_01jexample`, `ord_01jexample`.

Each model declares a `__prefix__` class variable and uses a generated default from `project.ids`:

```python
# src/project/ids.py
from ulid import ULID

def prefixed_ulid(prefix: str) -> str:
    return f"{prefix}_{str(ULID()).lower()}"

generate_prd_id = _make_generator("prd")
generate_ord_id = _make_generator("ord")
generate_itm_id = _make_generator("itm")
```

**Current prefixes:**

| Model     | Prefix | Example ID                         |
|-----------|--------|------------------------------------|
| Product   | `prd`  | `prd_01jq3v7k8m0000000000000000`   |
| Order     | `ord`  | `ord_01jq3v7k8m0000000000000000`   |
| OrderItem | `itm`  | `itm_01jq3v7k8m0000000000000000`   |

When adding new models, add a new generator to `project/ids.py` and follow the same pattern.

## Layer Details

### 1. Django Model (thin)

Models define the database schema only. No business methods, no managers with domain logic. Every model declares `__prefix__` and uses a `CharField` primary key with a ULID default.

```python
# src/products/models/product.py
from typing import ClassVar
from django.db import models
from project.ids import generate_prd_id

class Product(models.Model):
    __prefix__: ClassVar[str] = "prd"

    id = models.CharField(max_length=64, primary_key=True, default=generate_prd_id, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    def __str__(self):
        return self.name
```

### 2. Pydantic DTO

DTOs are the data contract between the repository layer and everything above it. They use `from_attributes=True` so they can be constructed directly from ORM instances. All ID fields are `str`.

```python
# src/products/dtos/product.py
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price: Decimal
    stock: int
```

When a DTO has a relation backed by a Django `RelatedManager` (e.g. `order.items`), add a field validator to coerce it to a list:

```python
# src/orders/dtos/order.py
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List

class OrderItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    order_id: str
    quantity: int
    price_at_purchase: Decimal

class OrderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: datetime
    total: Decimal
    items: List[OrderItemDTO] = []

    @field_validator("items", mode="before")
    @classmethod
    def coerce_related_manager(cls, v):
        if hasattr(v, "all"):
            return list(v.all())
        return v
```

### 3. Repository

Repositories encapsulate all ORM access. Every public method returns a DTO (or list of DTOs), never an ORM object. Use `model_validate(orm_obj)` for conversion. Use `prefetch_related` when the DTO includes nested relations. ID parameters are `str`.

```python
# src/products/repositories/product.py
from django.db import models
from ..models.product import Product
from ..dtos.product import ProductDTO

class ProductRepository:
    def create(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        product = Product.objects.create(name=name, price=price, stock=stock)
        return ProductDTO.model_validate(product)

    def get_by_id(self, product_id: str) -> ProductDTO:
        product = Product.objects.get(id=product_id)
        return ProductDTO.model_validate(product)

    def list_all(self) -> list[ProductDTO]:
        return [ProductDTO.model_validate(p) for p in Product.objects.all()]

    def decrement_stock(self, product_id: str, quantity: int) -> None:
        updated = Product.objects.filter(id=product_id, stock__gte=quantity).update(
            stock=models.F("stock") - quantity
        )
        if not updated:
            raise ValueError(f"Insufficient stock for product {product_id}")
```

For transactional operations spanning multiple ORM calls, use `@transaction.atomic`:

```python
# src/orders/repositories/order.py
from django.db import transaction

class OrderRepository:
    @transaction.atomic
    def create(self, items: list[dict]) -> OrderDTO:
        order = Order.objects.create(total=Decimal("0.00"))
        total = Decimal("0.00")
        for item_data in items:
            product = Product.objects.get(id=item_data["product_id"])
            OrderItem.objects.create(
                order=order, product=product,
                quantity=item_data["quantity"],
                price_at_purchase=product.price,
            )
            total += product.price * item_data["quantity"]
        order.total = total
        order.save()
        return OrderDTO.model_validate(
            Order.objects.prefetch_related("items").get(id=order.id)
        )
```

### 4. Service

Services receive repositories via constructor injection. They contain business logic -- validation, cross-entity coordination, computed values. They never touch the ORM directly.

```python
# src/orders/services/order.py
class OrderService:
    def __init__(self, repo: OrderRepository, product_repo: ProductRepository):
        self.repo = repo
        self.product_repo = product_repo

    def create_order(self, items: list[dict]) -> OrderDTO:
        # Business rule: validate stock before placing order
        for item in items:
            product = self.product_repo.get_by_id(item["product_id"])
            if product.stock < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for {product.name}: "
                    f"requested {item['quantity']}, available {product.stock}"
                )

        order = self.repo.create(items=items)

        # Decrement stock after successful order
        for item in items:
            self.product_repo.decrement_stock(item["product_id"], item["quantity"])

        return order
```

### 5. Dependency Injection with svcs

`svcs` provides a service locator container scoped per request.

**Registry** (application startup -- registers factories):

```python
# src/project/services.py
import svcs
from products.repositories.product import ProductRepository
from orders.repositories.order import OrderRepository

registry = svcs.Registry()
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)
```

**Middleware** (per-request container lifecycle):

```python
# src/project/middleware.py
import svcs
from .services import registry

class SvcsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        container = svcs.Container(registry)
        request.services = container
        try:
            return self.get_response(request)
        finally:
            container.close()
```

Add to `MIDDLEWARE` in settings:

```python
MIDDLEWARE = [
    # ... standard Django middleware ...
    "project.middleware.SvcsMiddleware",
]
```

**Usage in views** -- retrieve from `request.services`:

```python
repo = request.services.get(ProductRepository)
```

### 6. API Endpoints (django-ninja)

All API routes are defined centrally in `project/api.py`. Input schemas use `ninja.Schema`. Output schemas reuse the Pydantic DTOs. Use `Status(code, data)` for non-200 responses. ID path parameters are `str`.

```python
# src/project/api.py
from ninja import Router, Schema, Status
from products.dtos.product import ProductDTO
from products.repositories.product import ProductRepository
from products.services.product import ProductService

products_router = Router()

class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int

@products_router.get("/", response=list[ProductDTO])
def list_products(request):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return service.list_products()

@products_router.post("/", response={201: ProductDTO})
def create_product(request, payload: CreateProductIn):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return Status(201, service.create_product(
        name=payload.name, price=payload.price, stock=payload.stock
    ))
```

## Key Rules

- **ORM objects never cross the repository boundary.** If you find yourself accessing `.objects` in a service or view, move it to a repository.
- **DTOs are immutable data.** They carry no behaviour. Do not add methods that call the ORM.
- **Services are stateless.** They receive repos in `__init__` and operate on them. No class-level state.
- **One repo per aggregate root.** `OrderRepository` manages both `Order` and `OrderItem`. Don't make a separate `OrderItemRepository`.
- **Use `model_validate(obj)` with `from_attributes=True`** to convert ORM instances to DTOs. For related managers, add a `field_validator` with `mode="before"` that calls `.all()`.
- **Use `@transaction.atomic`** on repository methods that perform multiple writes.
- **Input schemas live in `project/api.py`**, not in the DTOs directory. Input and output schemas are separate concerns.
- **All IDs are prefixed ULID strings.** Never use UUIDs or auto-incrementing integers. Add new prefixes to `project/ids.py`.

## Dependencies

```
django>=6.0
django-ninja>=1.6
pydantic>=2.0
svcs>=25.1
python-ulid>=3.0
```
