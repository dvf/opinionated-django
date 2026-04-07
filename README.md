# Opinionated Django

An example project showing how I like to structure Django applications.

It's a fake e-commerce API (products and orders) that I use as a reference for building Django apps with proper boundaries. The patterns here solve real problems I've hit repeatedly: ORM objects leaking everywhere, untestable business logic, meaningless IDs in logs, and serializers doing six jobs at once.

## The Stack

**Core**

|                                                        |                                                |
|--------------------------------------------------------|------------------------------------------------|
| [Python 3.14](https://docs.python.org/3.14/)           | Latest version, free-threaded                  |
| [Django 6.0](https://docs.djangoproject.com/en/6.0/)   | Web framework                                  |
| [Celery](https://docs.celeryq.dev/)                    | Distributed task queue for reliable signals     |

**Libraries**

|                                                          |                                                |
|----------------------------------------------------------|------------------------------------------------|
| [django-ninja](https://django-ninja.dev/)                | Pydantic-native API layer (not DRF)            |
| [Pydantic v2](https://docs.pydantic.dev/latest/)         | Validation and serialization at the boundary   |
| [svcs](https://svcs.hynek.me/)                           | Dependency injection without magic             |
| [python-ulid](https://github.com/mdomke/python-ulid)    | Stripe-style prefixed IDs (`prd_01jq3v...`)    |

**Developer Tooling**

|                                                    |                                                |
|----------------------------------------------------|------------------------------------------------|
| [pytest](https://docs.pytest.org/)                 | Testing with mocked repos                      |
| [uv](https://docs.astral.sh/uv/)                  | Fast dependency management                     |
| [ruff](https://docs.astral.sh/ruff/)               | Linting and formatting                         |
| [pyrefly](https://github.com/facebook/pyrefly)     | Static type analysis                           |
| [SpecKit](https://speckit.dev/)                    | Feature specs, plans, and task generation       |

## Quick Start

```bash
uv sync
uv run python src/manage.py migrate
uv run python src/manage.py runserver
```

```bash
curl -s -X POST http://localhost:8000/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": "29.99", "stock": 100}'
```

```json
{
  "id": "prd_01jq3v7k8mfz3a4y9x0tn6bewh",
  "name": "Widget",
  "price": "29.99",
  "stock": 100
}
```

```bash
curl -s -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": "prd_01jq3v7k8mfz3a4y9x0tn6bewh", "quantity": 2}]}'
```

```json
{
  "id": "ord_01jq3v8p2ngx5b7r1w4sm9cdfk",
  "date": "2026-04-04T12:00:00Z",
  "total": "59.98",
  "items": [
    {
      "id": "itm_01jq3v8p2qhy6c8s2x5un0eglm",
      "product_id": "prd_01jq3v7k8mfz3a4y9x0tn6bewh",
      "order_id": "ord_01jq3v8p2ngx5b7r1w4sm9cdfk",
      "quantity": 2,
      "price_at_purchase": "29.99"
    }
  ]
}
```

```bash
uv run pytest
```

---

## The Opinions

### 1. Stripe-Style Prefixed IDs

```
prd_01jq3v7k8mfz3a4y9x0tn6bewh   ← Product
ord_01jq3v8p2ngx5b7r1w4sm9cdfk   ← Order
itm_01jq3v8p2qhy6c8s2x5un0eglm   ← OrderItem
```

UUIDs are unique but unreadable. When `f47ac10b-58cc-4372-a567-0e02b2c3d479` shows up in a log, you have no idea what it is. Auto-incrementing integers are guessable and leak how many records you have.

Every model gets a short prefix (`prd`, `ord`, `itm`) and a [ULID](https://github.com/ulid/spec). ULIDs are time-sortable, globally unique, and URL-safe. The prefix tells you what you're looking at everywhere it appears.

```python
# src/project/ids.py
from ulid import ULID

def prefixed_ulid(prefix: str) -> str:
    return f"{prefix}_{str(ULID()).lower()}"
```

```python
# src/products/models/product.py
class Product(models.Model):
    __prefix__: ClassVar[str] = "prd"

    id = models.CharField(
        max_length=64,
        primary_key=True,
        default=generate_prd_id,
        editable=False,
    )
```

New entity? Add a generator to `project/ids.py`. Done.

---

### 2. ORM Objects Never Leave the Repository

```
View → Service → Repository → ORM
                       ↑
          Pydantic DTOs go up
          ORM objects stay here
```

In most Django projects, ORM objects flow freely everywhere. Views touch querysets. Templates trigger lazy loads. Serializers reach into relations. The ORM becomes an invisible dependency threaded through every layer.

Here, repositories are the only code that touches the ORM. Every public method returns a Pydantic DTO. Everything above the repository boundary works with plain data.

```python
class ProductRepository:
    def create(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        product = Product.objects.create(name=name, price=price, stock=stock)
        return ProductDTO.model_validate(product)

    def get_by_id(self, product_id: str) -> ProductDTO:
        product = Product.objects.get(id=product_id)
        return ProductDTO.model_validate(product)
```

```python
class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price: Decimal
    stock: int
```

`model_validate()` with `from_attributes=True` does the conversion at the boundary. After that it's just data. No lazy loading, no surprise queries.

---

### 3. Thin Models

Django's "fat model" culture leads to models with business logic, validation, computed properties, and side effects. You can't test any of it without a database.

Models here are just schema. Business logic lives in services. Data access lives in repositories.

```python
# This is the entire model
class Product(models.Model):
    __prefix__: ClassVar[str] = "prd"

    id = models.CharField(max_length=64, primary_key=True, default=generate_prd_id, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    def __str__(self):
        return self.name
```

---

### 4. Services Own the Business Logic

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

Services take repos through the constructor. They validate, orchestrate, and coordinate, but they never touch the ORM. This makes them trivially testable, which brings us to:

---

### 5. Testing: Mock the Repo, Not the ORM

This is the payoff for all the layering. Because services only depend on repositories through constructor injection, you can test business logic with plain `MagicMock` objects. No database, no fixtures, no Django test runner overhead.

```python
# tests/orders/test_service.py
from unittest.mock import MagicMock

def test_rejects_insufficient_stock():
    product_repo = MagicMock()
    product_repo.get_by_id.return_value = ProductDTO(
        id="prd_fake", name="Widget", price=Decimal("10.00"), stock=2
    )

    order_repo = MagicMock()
    service = OrderService(order_repo, product_repo)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_order(items=[{"product_id": "prd_fake", "quantity": 10}])

    order_repo.create.assert_not_called()  # order was never placed
```

No `@pytest.mark.django_db`. No database setup. The test runs in microseconds and validates exactly one thing: the stock validation rule.

Compare this to how you'd normally test the same logic in Django: you'd need to create actual Product rows, worry about migrations, manage test database state, and hope your factory fixtures are in sync with your models. Here you just pass in a mock that returns a DTO.

Three test layers:

- **`test_repo.py`** hits the real database. Tests that ORM queries work and DTOs come back correctly.
- **`test_service.py`** mocks the repos. Tests business logic in complete isolation. This is the most valuable layer.
- **`test_api.py`** hits the HTTP layer with the Django test client. Integration tests that verify routing, serialization, and status codes.

---

### 6. Dependency Injection with svcs

Hard-coding `ProductRepository()` in views makes testing annoying. You end up patching imports or mocking at the module level.

[svcs](https://svcs.hynek.me/) gives you a service container scoped to each request. Middleware creates it, views pull from it, cleanup happens automatically.

```python
# Register once at startup
registry = svcs.Registry()
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)
```

```python
# Middleware attaches a container to each request
class SvcsMiddleware:
    def __call__(self, request):
        container = svcs.Container(registry)
        request.services = container
        try:
            return self.get_response(request)
        finally:
            container.close()
```

```python
# Views just ask for what they need
repo = request.services.get(ProductRepository)
service = ProductService(repo)
```

No decorators, no metaclasses, no magic.

---

### 7. Type-Safe Requests

```python
class ServiceRequest(HttpRequest):
    services: svcs.Container
```

```python
@products_router.get("/", response=List[ProductDTO])
def list_products(request: ServiceRequest):
    repo = request.services.get(ProductRepository)  # ← fully typed
```

`request.services.get(ProductRepository)` resolves to `ProductRepository` in the type checker. Your editor autocompletes it. pyrefly catches mistakes.

---

### 8. django-ninja, not DRF

DRF serializers blur the line between validation, serialization, and business logic. ViewSets hide too much. None of it works well with modern type checkers.

[django-ninja](https://django-ninja.dev/) is Pydantic-native. Input and output schemas are just Pydantic models.

```python
class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int

@products_router.post("/", response={201: ProductDTO})
def create_product(request: ServiceRequest, payload: CreateProductIn):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return Status(201, service.create_product(
        name=payload.name, price=payload.price, stock=payload.stock
    ))
```

Plain functions. Pydantic handles validation. DTOs are reused directly as response schemas.

---

## Project Structure

```
src/
├── project/                   # Config, API, DI, IDs
│   ├── api.py                 # All routes (django-ninja)
│   ├── ids.py                 # Prefixed ULID generation
│   ├── middleware.py           # svcs container lifecycle
│   ├── services.py             # DI registry
│   ├── types.py                # ServiceRequest
│   ├── settings.py
│   └── urls.py
├── products/
│   ├── models/product.py
│   ├── dtos/product.py
│   ├── repositories/product.py
│   ├── services/product.py
│   └── admin.py
└── orders/
    ├── models/order.py
    ├── dtos/order.py
    ├── repositories/order.py
    ├── services/order.py
    └── admin.py
tests/
├── products/
│   ├── test_api.py            # HTTP integration
│   ├── test_repo.py           # ORM + DTO conversion
│   └── test_service.py        # Mocked repos, business logic
└── orders/
    ├── test_api.py
    ├── test_repo.py
    └── test_service.py
```

Routes live in `project/api.py`, not scattered across apps. One file, every endpoint.

---

### 9. Reliable Signals with Celery

Django signals have a dirty secret: they're unreliable. If a receiver fails, the exception propagates back to the sender. If the process crashes after a transaction commits but before signals fire, receivers never run. There's no retry. You either get lucky or you don't.

This project implements the pattern from [Haki Benita's Reliable Django Signals](https://hakibenita.com/django-reliable-signals), adapted to use Celery instead of Django's Tasks framework.

**The problem:**

```
# Standard Django signals
with transaction.atomic():
    order.save()

post_save.send(sender=Order, instance=order)  # ← fires AFTER commit
                                                #   but what if we crash here?
                                                #   what if the receiver fails?
```

Three failure modes:
1. **Receiver failure kills the sender** — a broken email handler takes down order creation
2. **No delivery guarantee** — crash between commit and dispatch = lost signals
3. **No retry** — transient failures (network blip, service down) are permanent

**The fix: enqueue inside the transaction**

```
┌─────────────────────────────────┐
│  Database Transaction           │
│                                 │
│  1. Save Order                  │
│  2. Enqueue Celery task(s)      │  ← same transaction
│                                 │
│  COMMIT ─────────────────────── │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Celery Worker                  │
│                                 │
│  3. Execute receiver            │
│  4. Retry on failure            │
│                                 │
└─────────────────────────────────┘
```

Tasks are enqueued **inside** the same database transaction as the business operation. If the transaction rolls back, the tasks roll back too. If it commits, the tasks are guaranteed to be in the queue — even if the process crashes immediately after.

**Defining signals:**

```python
# src/orders/signals.py
from project.signals import ReliableSignal

order_created = ReliableSignal()
```

**Sending reliably (from the service layer):**

```python
# src/orders/services/order.py
class OrderService:
    def create_order(self, items: list[dict]) -> OrderDTO:
        with transaction.atomic():
            order = self.repo.create(items=items)

            order_created.send_reliable(
                sender=None,
                order_id=order.id,  # ← serializable args only, no model instances
            )

        return order
```

**Registering receivers (unchanged from Django):**

```python
# src/orders/receivers.py
from django.dispatch import receiver
from orders.signals import order_created

@receiver(order_created)
def on_order_created(order_id: str, **kwargs):
    # Send confirmation email, update analytics, trigger fulfillment...
    send_order_confirmation(order_id)
```

**What happens under the hood:**

1. `send_reliable()` serializes each registered receiver to a `module::qualname` string
2. For each receiver, it enqueues a Celery task **inside the current transaction**
3. On commit, Celery picks up the tasks and executes receivers asynchronously
4. On rollback, tasks are discarded — receivers never fire
5. If a receiver fails, Celery retries with exponential backoff

**Key rules:**
- Arguments must be JSON-serializable (pass IDs, not model instances)
- Receivers must be idempotent (at-least-once delivery, not exactly-once)
- Use `send_reliable()` inside a `transaction.atomic()` block
- Standard `send()` still works for cases where you don't need reliability

> **Credit**: This pattern is based on [Reliable Signals](https://hakibenita.com/django-reliable-signals) by [Haki Benita](https://hakibenita.com/). His original implementation uses Django 6.0's Tasks framework; this project substitutes Celery as the task backend.

---

## The Rules

1. ORM objects never cross the repository boundary
2. Models are schema only
3. Services are stateless -- repos in, DTOs out
4. One repo per aggregate root
5. All IDs are prefixed ULID strings
6. Dependencies come from the svcs container
7. Input schemas live in `project/api.py`, output DTOs live in each app
8. Service tests mock the repo, not the database
9. Side-effects use reliable signals — enqueued in the transaction, executed by Celery

---

## Working with Claude Code

This project includes a [`modern-django`](.claude/skills/modern-django/SKILL.md) skill for [Claude Code](https://claude.ai/code) that knows the full architecture — prefixed ULID IDs, repository pattern, Pydantic DTOs, svcs DI, django-ninja API, Celery reliable signals, and layered tests. When you ask Claude to add a new entity, endpoint, or business logic, invoke it with:

```
/modern-django add a shipping address to orders
```

It will scaffold every layer (model, DTO, repo, service, routes, admin, tests) following the conventions documented here.

Feature specifications are managed with [SpecKit](https://speckit.dev/) — specs live in `specs/` and are generated via `/speckit.specify`.

---

## License

MIT
