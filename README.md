# Opinionated Django

A reference architecture for building Django APIs the way they probably should be built — with clear boundaries, real types, and zero ORM leakage.

This is a fake e-commerce project (products & orders) that demonstrates a set of strong, deliberate choices about how to structure a modern Django application. Every decision here exists because the default Django way has a specific problem, and this is the fix.

## The Stack

| Tool             | Why                                                   |
|------------------|-------------------------------------------------------|
| **Python 3.14**  | Latest version, GIL-unlocked                          |
| **Django 6.0**   | Most mature Python web framework                      |
| **django-ninja** | Fast, Pydantic-native API framework (not DRF)         |
| **Pydantic v2**  | Data validation and serialization at the boundary     |
| **svcs**         | Dependency injection without magic                    |
| **python-ulid**  | Stripe-style prefixed IDs safe for public consumption |
| **uv**           | Fast, modern Python package management                |
| **ruff**         | Linting and formatting                                |
| **pyrefly**      | Static type analysis with Django compatibility        |

## Quick Start

```bash
uv sync
uv run python src/manage.py migrate
uv run python src/manage.py runserver
```

```bash
# Create a product
curl -X POST http://localhost:8000/products/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": "29.99", "stock": 100}'

# Response:
{
  "id": "prd_01jq3v7k8mfz3a4y9x0tn6bewh",
  "name": "Widget",
  "price": "29.99",
  "stock": 100
}
```

```bash
# Place an order
curl -X POST http://localhost:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": "prd_01jq3v7k8mfz3a4y9x0tn6bewh", "quantity": 2}]}'

# Response:
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

Run the tests:

```bash
uv run pytest
```

---

## The Opinions

### 1. Stripe-Style Prefixed IDs

```
"prd_01jq3v7k8mfz3a4y9x0tn6bewh"  ← Product
"ord_01jq3v8p2ngx5b7r1w4sm9cdfk"  ← Order
"itm_01jq3v8p2qhy6c8s2x5un0eglm"  ← OrderItem
```

**The problem:** UUIDs are great for uniqueness but terrible for humans. When you see `f47ac10b-58cc-4372-a567-0e02b2c3d479` in a log, you have no idea what it refers to. Auto-incrementing integers leak information about your database size and are guessable.

**The fix:** Every model gets a short prefix (`prd`, `ord`, `itm`) followed by a [ULID](https://github.com/ulid/spec). ULIDs are time-sortable, globally unique, and URL-safe. The prefix tells you what kind of thing you're looking at — in logs, in URLs, in your database, everywhere.

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

Adding a new entity? Add a generator to `project/ids.py` and follow the pattern. That's it.

---

### 2. ORM Objects Never Leave the Repository

```
View → Service → Repository → ORM
                       ↑
          Pydantic DTOs go up
          ORM objects stay here
```

**The problem:** In typical Django, ORM objects flow freely through your entire codebase. Views access querysets. Templates trigger lazy loads. Serializers reach into relations. The ORM becomes an invisible dependency woven through every layer, making things impossible to test in isolation and easy to break silently.

**The fix:** Repositories are the _only_ place that touches the ORM. Every public method returns a Pydantic DTO. The rest of your code doesn't know Django models exist.

```python
# src/products/repositories/product.py
class ProductRepository:
    def create(self, name: str, price: Decimal, stock: int) -> ProductDTO:
        product = Product.objects.create(name=name, price=price, stock=stock)
        return ProductDTO.model_validate(product)

    def get_by_id(self, product_id: str) -> ProductDTO:
        product = Product.objects.get(id=product_id)
        return ProductDTO.model_validate(product)
```

```python
# src/products/dtos/product.py
class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price: Decimal
    stock: int
```

`model_validate()` with `from_attributes=True` converts the ORM instance to a Pydantic object at the boundary. After that, it's just data — no lazy loading, no accidental queries, no surprises.

---

### 3. Models Are Just Schema

**The problem:** Django's "fat model" pattern encourages stuffing business logic, validation, computed properties, and side effects into model classes. This makes them untestable without a database and tightly couples your domain logic to Django's ORM lifecycle.

**The fix:** Models define the schema. Period. Business logic goes in services. Data access goes in repositories. Models are a thin mapping between Python and your database, nothing more.

```python
# src/products/models/product.py — the ENTIRE model
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
# src/orders/services/order.py
class OrderService:
    def __init__(self, repo: OrderRepository, product_repo: ProductRepository):
        self.repo = repo
        self.product_repo = product_repo

    def create_order(self, items: List[Dict[str, Any]]) -> OrderDTO:
        # Validate stock BEFORE creating the order
        for item in items:
            product = self.product_repo.get_by_id(item["product_id"])
            if product.stock < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for product {product.name}: "
                    f"requested {item['quantity']}, available {product.stock}"
                )

        order = self.repo.create(items=items)

        # Decrement stock AFTER successful creation
        for item in items:
            self.product_repo.decrement_stock(item["product_id"], item["quantity"])

        return order
```

Services receive repositories through their constructor. They coordinate, validate, and orchestrate — but they never touch the ORM directly. This means you can test business logic by passing in fake repositories. No database required.

---

### 5. Dependency Injection with svcs

**The problem:** Hard-coding `ProductRepository()` inside views or services makes testing painful. You end up patching imports, mocking at the module level, or building elaborate fixtures just to swap out a dependency.

**The fix:** [svcs](https://svcs.hynek.me/) provides a service container scoped to each request. Middleware creates the container, views pull from it, and it's cleaned up automatically.

```python
# src/project/services.py — register once at startup
registry = svcs.Registry()
registry.register_factory(ProductRepository, ProductRepository)
registry.register_factory(OrderRepository, OrderRepository)
```

```python
# src/project/middleware.py — container per request
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
# In any view — just ask for what you need
repo = request.services.get(ProductRepository)
service = ProductService(repo)
```

No decorators. No metaclasses. No framework magic. Just a container you can inspect, replace, and test.

---

### 6. Type-Safe Request Objects

```python
# src/project/types.py
class ServiceRequest(HttpRequest):
    """HttpRequest with a svcs.Container attached by SvcsMiddleware."""
    services: svcs.Container
```

```python
# In views — fully typed
@products_router.get("/", response=List[ProductDTO])
def list_products(request: ServiceRequest):
    repo = request.services.get(ProductRepository)  # ← type checker knows this
```

`request.services.get(ProductRepository)` is fully typed — your editor autocompletes the return type, and the type checker catches mistakes. No `# type: ignore`, no guessing.

---

### 7. django-ninja Over DRF

**The problem:** Django REST Framework was designed for a different era. Serializers blur the line between validation, serialization, and business logic. ViewSets hide too much. The permission system is inflexible. And none of it plays well with modern type checkers.

**The fix:** [django-ninja](https://django-ninja.dev/) is Pydantic-native. Input schemas are just Pydantic models. Output schemas are just Pydantic models. There's nothing else to learn.

```python
# Input — a ninja Schema (which is just a Pydantic BaseModel)
class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int

# Output — your existing DTO, reused directly
@products_router.post("/", response={201: ProductDTO})
def create_product(request: ServiceRequest, payload: CreateProductIn):
    repo = request.services.get(ProductRepository)
    service = ProductService(repo)
    return Status(201, service.create_product(
        name=payload.name, price=payload.price, stock=payload.stock
    ))
```

Views are plain functions. Validation happens automatically via Pydantic. No serializer classes, no `many=True`, no `SerializerMethodField` hacks.

---

## Project Structure

```
src/
├── project/                   # Django config, API, DI, IDs
│   ├── api.py                 # All API routes (django-ninja)
│   ├── ids.py                 # Prefixed ULID generation
│   ├── middleware.py           # svcs container lifecycle
│   ├── services.py             # DI registry
│   ├── types.py                # ServiceRequest type
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── products/
│   ├── models/product.py       # Thin model
│   ├── dtos/product.py         # Pydantic DTO
│   ├── repositories/product.py # Data access
│   ├── services/product.py     # Business logic
│   └── admin.py
└── orders/
    ├── models/order.py         # Order + OrderItem models
    ├── dtos/order.py           # Order + OrderItem DTOs
    ├── repositories/order.py   # Transactional data access
    ├── services/order.py       # Stock validation, orchestration
    └── admin.py
tests/
├── products/
│   ├── test_api.py
│   └── test_repo.py
└── orders/
    ├── test_api.py
    └── test_repo.py
```

**Key structural decision:** API routes live in `project/api.py`, not scattered across apps. This gives you a single place to see every endpoint in your system. Input schemas live alongside the routes. Output DTOs live in each app's `dtos/` directory and are reused directly.

---

## The Rules

1. **ORM objects never cross the repository boundary.** If you're accessing `.objects` in a service or view, you're doing it wrong.
2. **Models are schema only.** No business methods, no custom managers with domain logic.
3. **Services are stateless.** They receive repos in `__init__`, do work, return DTOs.
4. **One repository per aggregate root.** `OrderRepository` manages both `Order` and `OrderItem`. There is no `OrderItemRepository`.
5. **All IDs are prefixed ULID strings.** No UUIDs, no integers, no exceptions.
6. **Dependencies come from the container.** Nothing is instantiated directly in views.
7. **Input schemas live in `project/api.py`.** Output DTOs live in each app. They are separate concerns.

---

## License

MIT
