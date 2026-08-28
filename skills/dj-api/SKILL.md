---
name: dj-api
description: Structure Django Ninja API endpoints, routers, schemas, and exception handling. Complements dj-architecture Layer 7 with concrete conventions for router configuration, schema naming, status codes, error handling, and OpenAPI tags. Use when creating or modifying API endpoints, designing request/response shapes, or wiring a new resource into the NinjaAPI mount.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Django Ninja API Conventions

You are implementing or restructuring Django Ninja endpoints in an opinionated project. These conventions sit on top of `dj-architecture` Layer 7 (project-scoped `src/project/api/` package with per-resource subdirectories). Every convention below is mandatory.

## BEFORE WRITING CODE

Read:

- `src/project/api/__init__.py` — existing `NinjaAPI()` instance, exception handlers, mounted routers
- `src/project/api/<resource>/` — any existing resource packages to understand local conventions
- `src/project/types.py` — `AuthedRequest` and any related request narrowings
- The service you're fronting — handlers are thin dispatchers to registered services

---

## Directory Layout

The API MUST live in a package directory, never a single `api.py` file:

```
src/project/
└── api/
    ├── __init__.py          # NinjaAPI() instance, exception handlers, mounts routers
    ├── products/
    │   ├── __init__.py      # from .routes import router
    │   ├── routes.py        # @router.get/post/put/delete handlers
    │   └── schemas.py       # ninja.Schema input types
    ├── orders/
    │   ├── __init__.py
    │   ├── routes.py
    │   └── schemas.py
    └── auth/
        ├── __init__.py
        ├── routes.py
        └── schemas.py
```

**Rules:**

1. **One resource per subpackage.** Filenames match the resource plural (`products/`, `orders/`, `invoices/`).
2. **`routes.py`** — handler functions. Nothing else lives here.
3. **`schemas.py`** — `ninja.Schema` input types. Output types reuse DTOs from the owning app (never redefine).
4. **`__init__.py` re-exports the router** via `from .routes import router` + `__all__ = ["router"]`.
5. **Shared cross-resource schemas** — when a schema is truly generic (e.g., `PaginationParams`, `ErrorResponse`), put it in `src/project/api/_shared.py` — never duplicate across resources.
6. **`schemas.py` splits to a directory** — if `schemas.py` grows past the 400-line hard limit (`dj-architecture` Module Size rule), convert to `schemas/` with one module per schema group (e.g., `schemas/create.py`, `schemas/filters.py`) and re-export via `schemas/__init__.py`.

---

## Router Configuration

Every resource's `routes.py` declares exactly one `Router()` instance named `router`:

```python
from ninja import Router

router = Router(
    auth=JWTAuth(),           # mandatory — see Auth below
    tags=["products"],         # mandatory — see Tags below
)
```

**Rules:**

1. **`auth=` is mandatory on every router.** Public endpoints opt out explicitly per-handler with `auth=None`; this makes the default safe and the exception visible.
2. **`tags=` is mandatory** and MUST be the resource plural in lowercase (`["products"]`, `["orders"]`, `["invoice_items"]`). Tags group endpoints in the OpenAPI docs.
3. **No per-handler `tags=` overrides** unless a handler genuinely belongs to a different concept. Consistency across the router is the default.
4. **One router per resource subpackage.** Never declare multiple `Router()` instances in one `routes.py`. If the resource has enough surface that a single file is messy, split the resource.

---

## Handler Conventions

```python
from typing import List

from ninja import Router
from ninja.responses import codes_4xx

from products.dtos.product import ProductDTO
from products.services.product import ProductService
from project.services import get
from project.types import AuthedRequest

from .schemas import CreateProductIn, UpdateProductIn

router = Router(auth=JWTAuth(), tags=["products"])


@router.get("/", response=List[ProductDTO], summary="List products")
def list_products(request: AuthedRequest):
    return get(ProductService).list_products()


@router.post("/", response={201: ProductDTO}, summary="Create product")
def create_product(request: AuthedRequest, payload: CreateProductIn):
    return 201, get(ProductService).create_product(
        name=payload.name, price=payload.price, stock=payload.stock
    )


@router.get("/{product_id}/", response=ProductDTO, summary="Get product by id")
def get_product(request: AuthedRequest, product_id: str):
    return get(ProductService).get_product(product_id)


@router.put("/{product_id}/", response=ProductDTO, summary="Update product")
def update_product(
    request: AuthedRequest, product_id: str, payload: UpdateProductIn
):
    return get(ProductService).update_product(product_id, **payload.dict())


@router.delete("/{product_id}/", response={204: None}, summary="Delete product")
def delete_product(request: AuthedRequest, product_id: str):
    get(ProductService).delete_product(product_id)
    return 204, None
```

**Rules:**

1. **First handler arg is always `request: AuthedRequest`** — never untyped, never plain `HttpRequest`. `AuthedRequest` narrows `request.user` to an authenticated user.
2. **ID path params are always `str`** — matches the prefixed-ULID convention (`prd_01jq...`).
3. **Handlers are thin.** One line of logic when possible: `return get(Service).method(args)`. No try/except, no business logic, no ORM. Errors bubble to the central exception handler.
4. **`summary="..."`** on every endpoint — shows in OpenAPI docs, reads naturally ("Create product", "List orders"), starts with a capital verb.
5. **Response type annotations drive OpenAPI** — `response=List[ProductDTO]` for lists, `response=ProductDTO` for single, `response={201: ProductDTO}` for creates, `response={204: None}` for deletes.

---

## Status Codes

Use HTTP status codes consistently:

| Code | When |
|---|---|
| `200` | Successful GET, PUT, PATCH with body |
| `201` | Successful POST that creates a resource. Return `(201, dto)`. |
| `204` | Successful DELETE or void action. Return `(204, None)`. |
| `400` | Validation error — raised as `ValueError` in the service, mapped by the exception handler |
| `401` | Unauthenticated — handled automatically by `JWTAuth()` |
| `403` | Forbidden — raised as `PermissionError` in the service |
| `404` | Not found — raised as `LookupError` in the service |

**Rules:**

1. **POST that creates returns 201**, not 200. The `(201, dto)` tuple pattern makes this explicit.
2. **DELETE returns 204, not 200.** Empty body.
3. **Do not return 500 deliberately.** 500 is for bugs; a service raising `ValueError` is not a bug.
4. **Never return `{"error": "..."}` from a handler.** The exception handler shape is `{"detail": "..."}` — consistent across the entire API.

---

## Schemas

Input schemas live in `schemas.py` next to the routes:

```python
from decimal import Decimal

from ninja import Schema
from pydantic import Field


class CreateProductIn(Schema):
    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    stock: int = Field(0, ge=0)


class UpdateProductIn(Schema):
    name: str | None = None
    price: Decimal | None = None
    stock: int | None = None
```

**Rules:**

1. **Naming:** input schemas are `<Verb><Noun>In` (`CreateProductIn`, `UpdateProductIn`, `PatchOrderIn`). Query-param schemas are `<Noun>Filters` (`ProductFilters`). Never `ProductCreateSerializer` or similar DRF carry-over.
2. **Output schemas are the DTOs from the owning app** — do not redefine. `response=ProductDTO`, not `response=ProductOut`.
3. **Use Pydantic's `Field(...)` for validation** — `min_length`, `max_length`, `gt`, `ge`, `le`, `lt`, `regex`, `decimal_places`. Rely on Pydantic for input validation, raise `ValueError` in the service for semantic validation.
4. **Partial update schemas use `| None` with `None` default** — every field optional. The service treats `None` as "don't change".

---

## Exception Handlers

`src/project/api/__init__.py` owns a single set of exception handlers that map Python exceptions to HTTP responses. Handlers in `routes.py` never try/except — they raise and let the central handler shape the response.

```python
# src/project/api/__init__.py
from ninja import NinjaAPI

from project.api.products import router as products_router
from project.api.orders import router as orders_router

api = NinjaAPI()

api.add_router("/products", products_router)
api.add_router("/orders", orders_router)


@api.exception_handler(ValueError)
def on_value_error(request, exc: ValueError):
    return api.create_response(request, {"detail": str(exc)}, status=400)


@api.exception_handler(LookupError)
def on_lookup_error(request, exc: LookupError):
    return api.create_response(request, {"detail": str(exc)}, status=404)


@api.exception_handler(PermissionError)
def on_permission_error(request, exc: PermissionError):
    return api.create_response(request, {"detail": str(exc)}, status=403)
```

**Rules:**

1. **The error response shape is always `{"detail": "..."}`.** Never a different shape per exception.
2. **Services raise plain Python exceptions** — `ValueError` (bad input), `LookupError` (missing record), `PermissionError` (forbidden). They do NOT know about HTTP.
3. **Never add a 4th exception class** without updating this rule. The three above cover 99% of cases; adding domain-specific exceptions bloats the service layer and drifts from Python's built-ins.
4. **`exc.args[0]` becomes the user-facing message.** Write service error messages accordingly — "Product not found" not "404 product no exist".

---

## Mounting New Resources

To add a new resource (e.g., `invoices`):

1. Create `src/project/api/invoices/` with `__init__.py`, `routes.py`, `schemas.py`
2. Define `router = Router(auth=JWTAuth(), tags=["invoices"])` in `routes.py` with handlers
3. In `src/project/api/invoices/__init__.py` add `from .routes import router` and `__all__ = ["router"]`
4. In `src/project/api/__init__.py` add the import and mount:
   ```python
   from project.api.invoices import router as invoices_router

   api.add_router("/invoices", invoices_router)
   ```

No other wiring required. The resource is now on the OpenAPI docs under the `invoices` tag.

---

## Verify

After adding or modifying endpoints:

```bash
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest tests/api/<resource>
```

- All must pass.
- Service tests (without DB) prove the business logic; API tests (with DB via `@pytest.mark.django_db`) prove the HTTP wiring.
- See `dj-pytest` for the full three-layer test convention.

---

## Checklist

- [ ] API lives in `src/project/api/` package, never `api.py`
- [ ] One resource per subpackage with `routes.py` + `schemas.py` + `__init__.py`
- [ ] Every router has `auth=` and `tags=` configured
- [ ] Every handler first arg is `request: AuthedRequest`
- [ ] Every handler has `summary="..."` and typed `response=`
- [ ] ID path params are `str`
- [ ] Handlers are thin — one-line delegation to a registered service
- [ ] POST creates return 201, DELETE returns 204
- [ ] Input schemas named `<Verb><Noun>In`
- [ ] Output types reuse app DTOs — never redefined
- [ ] No try/except in handlers — errors bubble to central exception handler
- [ ] Error response shape is `{"detail": "..."}` for all handled exceptions
- [ ] Resource mounted in `src/project/api/__init__.py` via `api.add_router(...)`
- [ ] ruff, pyrefly, pytest all pass
