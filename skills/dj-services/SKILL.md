---
name: dj-services
description: Structure Django business logic as plain services that receive their dependencies via constructor injection, and wire them through an svcs registry so they can be resolved anywhere — views, Celery tasks, management commands, tests. Use when adding a new service, refactoring fat views or model methods into a service, wiring a service into the registry, or explaining where business logic should live in this project.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Services + svcs Dependency Injection

This project separates Django's framework concerns from business logic using a plain service layer, wired with the [svcs](https://svcs.hynek.me) service locator. The result:

- **Views are one-liners.** They pull a wired service and call a method.
- **Services contain the business logic.** They take repositories (and other services) via `__init__`, call methods on them, and return DTOs.
- **Services never import Django ORM or models.** Every test can run without a database.
- **One registry, one `get[T]()` helper.** The same call works in views, tasks, commands, anywhere.

## Why svcs Instead of Module-Level Singletons or a Custom Container

- `svcs` is a tiny, typed, well-maintained service locator — no metaclasses, no decorators, no framework coupling.
- Factories are lazy: a service is constructed only when something asks for it.
- Generic `get[T](type[T]) -> T` preserves types through IDE/type-checker inference.
- Swapping an implementation in tests is a one-line factory override.
- No import-order gymnastics: the registry is populated once at startup and then used by name.

## The Registry — `src/project/services.py`

```python
import svcs

from products.repositories.product import ProductRepository
from products.services.product import ProductService
from orders.repositories.order import OrderRepository
from orders.services.order import OrderService

registry = svcs.Registry()

# --- Repositories ---------------------------------------------------------
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)


# --- Services (factories pull repos from the container) ------------------
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
    """Resolve a service from the registry. Works anywhere — views, tasks, commands, tests."""
    return svcs.Container(registry).get(service_type)
```

Patterns to follow:

- **Repositories register themselves.** Use `register_factory(Repo, Repo)` — the class is its own factory because repositories take no constructor arguments.
- **Services register via a named factory.** `_<entity>_service_factory(container)` resolves every dependency from the container and hands it to the service's `__init__`. No hidden imports, no module-level singletons.
- **Register in dependency order.** Repos before services, lower-level services before higher-level ones. `svcs` doesn't enforce this, but it keeps the file readable.
- **One registry per project.** Don't create ad-hoc registries — everything goes through `project.services.registry`.

## Writing a Service

File: `src/<app>/services/<entity>.py`

```python
from decimal import Decimal
from typing import List

from ..dtos.product import ProductDTO
from ..repositories.product import ProductRepository


class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo

    def create_product(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        return self.repo.create(name=name, price=price, stock=stock)

    def get_product(self, product_id: str) -> ProductDTO:
        return self.repo.get_by_id(product_id)

    def list_products(self) -> List[ProductDTO]:
        return self.repo.list_all()
```

Rules:

- **Dependencies come in through `__init__`.** The service never instantiates its own repositories or services. If a service needs another service, pass it in.
- **Zero ORM.** No `.objects`, no `F()` / `Q()`, no model imports, no `select_related`. All database access goes through a repository.
- **Every public method returns a DTO or `list[DTO]`.** Never a model instance, never a queryset.
- **ID arguments are `str`.** See the `dj-prefixed-ulids` skill.
- **Business rules live here.** Validation, orchestration across repositories, invariant checks, error raising — all of it.
- **Services are stateless.** They hold references to their dependencies and nothing else. No caches, no counters, no module-level state.
- **Raise plain exceptions.** Use `ValueError`, `PermissionError`, domain-specific exceptions — not `Http404` or anything Django-flavored. The view layer turns them into HTTP responses.

### Cross-Entity Logic

When a service method touches more than one aggregate — e.g. creating an order that decrements product stock — inject both repositories and orchestrate them. Example from `OrderService`:

```python
class OrderService:
    def __init__(self, repo: OrderRepository, product_repo: ProductRepository):
        self.repo = repo
        self.product_repo = product_repo

    def create_order(self, items: List[Dict[str, Any]]) -> OrderDTO:
        for item in items:
            product = self.product_repo.get_by_id(item["product_id"])
            if product.stock < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for product {product.name}: "
                    f"requested {item['quantity']}, available {product.stock}"
                )

        order = self.repo.create(items=items)

        for item in items:
            self.product_repo.decrement_stock(item["product_id"], item["quantity"])

        return order
```

Notes:

- The service orchestrates two repositories but touches zero ORM.
- If a multi-repo write needs atomicity, wrap it in `with transaction.atomic():` — that's one of the very few `django.db` imports allowed in a service.
- Never call another service from inside a service unless that service is explicitly injected. No hidden `get(...)` calls inside service methods.

## Resolving a Service

### From a view (django-ninja)

```python
from project.services import get
from project.types import AuthedRequest


@products_router.post("/", response={201: ProductDTO})
def create_product(request: AuthedRequest, payload: CreateProductIn):
    service = get(ProductService)
    return Status(201, service.create_product(**payload.dict()))
```

Annotating `request` as `AuthedRequest` (defined in `src/project/types.py`) makes the auth contract explicit and narrows `request.user` to a guaranteed-authenticated Django `User`. This is a **typing contract**, not runtime enforcement — auth is still expected to be wired via middleware or ninja's `auth=` parameter.

### From a Celery task

```python
from celery import shared_task

from project.services import get
from products.services.product import ProductService


@shared_task
def reprice_product(product_id: str, new_price: str) -> None:
    service = get(ProductService)
    service.update_price(product_id, Decimal(new_price))
```

### From a management command

```python
from django.core.management.base import BaseCommand

from project.services import get
from products.services.product import ProductService


class Command(BaseCommand):
    def handle(self, *args, **options):
        service = get(ProductService)
        for dto in service.list_products():
            self.stdout.write(dto.name)
```

The same `get()` call works in all three contexts because the registry is global and the container is cheap to construct.

## Testing

Services are tested **without a database**. Pass in a `MagicMock` for each repository, configure its return values, and assert on the service's behavior.

```python
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from products.dtos.product import ProductDTO
from products.services.product import ProductService


def test_create_product_delegates_to_repo():
    repo = MagicMock()
    expected = ProductDTO(id="prd_fake", name="Widget", price=Decimal("9.99"), stock=5)
    repo.create.return_value = expected

    service = ProductService(repo)
    result = service.create_product(name="Widget", price=Decimal("9.99"), stock=5)

    assert result is expected
    repo.create.assert_called_once_with(name="Widget", price=Decimal("9.99"), stock=5)


def test_create_order_rejects_insufficient_stock():
    order_repo = MagicMock()
    product_repo = MagicMock()
    product_repo.get_by_id.return_value = ProductDTO(
        id="prd_fake", name="Widget", price=Decimal("9.99"), stock=1
    )

    service = OrderService(order_repo, product_repo)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_order(items=[{"product_id": "prd_fake", "quantity": 5}])

    order_repo.create.assert_not_called()
```

This is the most important test layer — it proves the business logic is correct independently of Django, migrations, fixtures, or the database. If a service's tests need `@pytest.mark.django_db`, something has leaked: find the ORM call and push it back into a repository.

### Overriding a Service in Tests

For integration tests that go through the API, override a factory to substitute a fake or a stub:

```python
from project.services import registry
from products.services.product import ProductService


@pytest.fixture
def fake_product_service():
    fake = MagicMock(spec=ProductService)
    registry.register_factory(ProductService, lambda _: fake)
    yield fake
    # svcs re-registers on next call; reset to the real factory if other tests need it.
```

## Common Mistakes

- **Importing models in a service.** If you see `from app.models import X`, the service is doing ORM work. Move it to the repository.
- **Calling `SomeRepository()` inside a service method.** Inject it via `__init__` and hold the reference.
- **Returning querysets or model instances from a service.** Always return DTOs.
- **Putting business logic in the view.** The view should only decode input, call `get(SomeService).method(...)`, and pass the result back.
- **Registering a service with `register_factory(Service, Service)`.** That only works for repositories because they take no arguments. Services need a factory that resolves their dependencies.
- **Reaching into `request.user` from the service.** Pass the caller's identity as an explicit argument (`user_id: str`) so the service stays framework-agnostic.

## Verify

- Every service under `src/<app>/services/` has an `__init__` that takes its dependencies explicitly.
- No file under `src/<app>/services/` imports from `django.db.models`, `<app>.models`, or uses `.objects`.
- Every service in the project is registered in `src/project/services.py` with a factory that resolves its dependencies from the container.
- Service tests do not use `@pytest.mark.django_db`.

```bash
uv run ruff check src
uv run pyrefly check src
uv run pytest
```
