---
name: scaffold
description: Set up a Django project into the op-django layout so the architecture, signals, and settings skills have a foundation to build on. Use when starting a new project from scratch, or when converting an existing Django project to follow this opinionated structure. Creates the src/project/ shell (ids, services registry, api, reliable signals), installs dependencies with uv, and establishes the per-app directory conventions.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Scaffold an op-django Project

You are preparing a Django project to use the op-django patterns. After this skill runs, the `architecture` and `signals` skills can add features on top without any further setup.

## BEFORE WRITING CODE

Figure out which situation you're in:

- **Greenfield** — no Django project exists yet. You will run `uv init` and `django-admin startproject`, then transform the result.
- **Existing Django project** — a `manage.py`, `settings.py`, and at least one app already exist. You will add the `src/project/` shell alongside what's there and relocate files only if asked.

Read `pyproject.toml` (if present) and locate `manage.py` and `settings.py` so you know the project's current layout. Confirm with the user before moving any existing files.

## Target Layout

```
src/
  manage.py
  project/
    __init__.py
    settings.py
    urls.py
    wsgi.py
    asgi.py
    api/
      __init__.py   # NinjaAPI() instance, exception handlers, mounts all resource routers
      <resource>/
        __init__.py  # re-exports router
        routes.py    # handler functions
        schemas.py   # ninja.Schema input types
    types.py        # AuthedRequest and other shared typing aliases
    ids.py          # prefixed ULID generators
    services.py    # svcs registry + get() helper
    signals.py     # ReliableSignal base + send_reliable machinery
  <app>/
    __init__.py
    apps.py
    admin.py
    models/
      __init__.py
      <entity>.py
    dtos/
      __init__.py
      <entity>.py
    repositories/
      __init__.py
      <entity>.py
    services/
      __init__.py
      <entity>.py
    signals.py      # optional, defines ReliableSignal instances
    receivers.py    # optional, @receiver handlers — must be idempotent
tests/
  <app>/
    test_repo.py
    test_service.py
    test_api.py
pyproject.toml
```

Per-app `models/`, `dtos/`, `repositories/`, `services/` are **packages**, not single files — one module per entity.

## Step 1: Dependencies

Use `uv` for everything. Never `pip` or `poetry`.

```bash
uv add 'django>=6.0' 'django-ninja>=1.6' 'pydantic>=2.0' 'svcs>=25.1' \
       'python-ulid>=3.0' 'celery>=5.4' python-decouple
uv add --dev ruff 'pyrefly>=0.42' django-stubs pytest pytest-django
```

Pyrefly auto-recognizes Django constructs as long as `django-stubs` is installed — no plugin, no `mypy_django_plugin`-style config. See [pyrefly.org/en/docs/django](https://pyrefly.org/en/docs/django/) for the current support matrix.

## Step 2: `src/project/ids.py`

```python
from ulid import ULID


def prefixed_ulid(prefix: str) -> str:
    return f"{prefix}_{str(ULID()).lower()}"


def _make_generator(prefix: str):
    def generate() -> str:
        return prefixed_ulid(prefix)

    generate.__name__ = f"generate_{prefix}_id"
    generate.__qualname__ = f"generate_{prefix}_id"
    return generate


# Add one generator per aggregate root, with a unique 3-4 char prefix.
# Example:
# generate_prd_id = _make_generator("prd")
```

## Step 3: `src/project/services.py`

```python
import svcs

registry = svcs.Registry()

# Register repositories and services here as the project grows.
# Example:
# from products.repositories.product import ProductRepository
# from products.services.product import ProductService
#
# registry.register_factory(ProductRepository, ProductRepository)
#
# def _product_service_factory(container: svcs.Container) -> ProductService:
#     return ProductService(container.get(ProductRepository))
#
# registry.register_factory(ProductService, _product_service_factory)


def get[T](service_type: type[T]) -> T:
    """Get a service from the registry. Works anywhere — views, tasks, commands."""
    return svcs.Container(registry).get(service_type)
```

## Step 4a: `src/project/types.py`

Narrows `request.user` to a guaranteed-authenticated Django `User` so handlers don't have to deal with `AnonymousUser` unions.

```python
from django.contrib.auth.models import User
from django.http import HttpRequest


class AuthedRequest(HttpRequest):
    """
    An HttpRequest whose `user` attribute is guaranteed to be an authenticated User.

    Use as the first-argument annotation on any django-ninja handler that requires
    auth. The narrowing is a contract, not runtime enforcement — pair this with
    ninja's `auth=` on the router or a middleware that rejects anonymous requests.
    """
    user: User  # type: ignore[assignment]
```

## Step 4b: `src/project/api/` package

The API lives in a package, not a single file. `src/project/api/__init__.py` owns the `NinjaAPI()` instance and central exception handlers, and mounts one router per resource subpackage. Each resource subpackage (`src/project/api/<resource>/`) contains `routes.py` (handler functions), `schemas.py` (ninja `Schema` input types), and an `__init__.py` that re-exports the router.

`src/project/api/__init__.py`:

```python
from ninja import NinjaAPI

# Import resource routers and mount them below.
# from project.api.products import router as products_router

api = NinjaAPI()

# api.add_router("/products", products_router)


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

Example resource subpackage — `src/project/api/products/routes.py`:

```python
from typing import List

from ninja import Router

from products.dtos.product import ProductDTO
from products.services.product import ProductService
from project.services import get
from project.types import AuthedRequest

from .schemas import CreateProductIn

router = Router()


@router.get("/", response=List[ProductDTO])
def list_products(request: AuthedRequest):
    return get(ProductService).list_products()
```

`src/project/api/products/schemas.py`:

```python
from decimal import Decimal

from ninja import Schema


class CreateProductIn(Schema):
    name: str
    price: Decimal
    stock: int
```

`src/project/api/products/__init__.py`:

```python
from .routes import router

__all__ = ["router"]
```

To add a new resource router: (a) create `src/project/api/<resource>/` with `routes.py`, `schemas.py`, and `__init__.py`, then (b) import and mount the router in `src/project/api/__init__.py` via `api.add_router("/<resource>", <resource>_router)`.

Wire `api.urls` into `src/project/urls.py`:

```python
from django.contrib import admin
from django.urls import path
from project.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

## Step 5: `src/project/signals.py` — Reliable Signals

This module provides the `ReliableSignal` base that apps import. Receivers run asynchronously via Celery, and `send_reliable()` enqueues them inside the current DB transaction so rollbacks are respected.

```python
import json

from celery import shared_task
from django.db import transaction
from django.dispatch import Signal
from django.utils.module_loading import import_string


@shared_task
def _dispatch_reliable_receiver(receiver_path: str, kwargs_json: str) -> None:
    receiver = import_string(receiver_path)
    receiver(**json.loads(kwargs_json))


class ReliableSignal(Signal):
    """A Django Signal whose receivers run asynchronously via Celery.

    - `send_reliable()` must be called inside a `transaction.atomic()` block.
    - Receiver tasks are enqueued on transaction commit, so rollbacks are respected.
    - Delivery is at-least-once. Every receiver MUST be idempotent.
    - Arguments MUST be JSON-serializable (pass IDs, never model instances).
    """

    def send_reliable(self, sender, **kwargs) -> None:
        payload = json.dumps(kwargs)
        for _, receiver in self._live_receivers(sender):
            path = f"{receiver.__module__}.{receiver.__qualname__}"
            transaction.on_commit(
                lambda p=path: _dispatch_reliable_receiver.delay(p, payload)
            )
```

This is a minimal implementation — feel free to harden it (dead-letter queue, replay tooling, explicit retry policy) as the project matures.

## Step 6: Celery

Create `src/project/celery.py`:

```python
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

app = Celery("project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

In `src/project/__init__.py`:

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

## Step 7: Settings

Hand off to the **settings** skill to lay out `settings.py` with banner sections. At minimum it must include:

- `INSTALLED_APPS` with each project app as `"<app>.apps.<App>Config"`
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` (read via `python-decouple`)
- `DEFAULT_AUTO_FIELD` is irrelevant — all PKs are ULID `CharField`s

## Step 8: Tooling config in `pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pyrefly]
project-includes = ["src"]
python-version = "3.12"

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "project.settings"
python_files = ["test_*.py"]
pythonpath = ["src"]
```

**Pyrefly + Django caveats** (from [pyrefly.org/en/docs/django](https://pyrefly.org/en/docs/django/)):

- Pyrefly has **built-in** Django support. Install `django-stubs` and it just works — no plugin to enable, no extra `[tool.pyrefly]` keys required.
- **Reverse relations are not yet supported.** Accessing `user.order_set` (the implicit reverse manager Django generates from a `ForeignKey`) will flag as an attribute error. Work around it in the repository layer by either (a) querying the child model directly — `OrderRepository().list_for_user(user_id)` — or (b) using an explicit `related_name` and a narrow `cast` / `# type: ignore[attr-defined]` at the call site. Do not paper over this in services or DTOs; push it down to the repo.
- **`ManyRelatedManager` is generic over `[Parent, Model]`** rather than the concrete child type (unlike mypy's django-plugin). For DTO coercion this doesn't matter — the `coerce_related_manager` validator handles it — but don't rely on pyrefly to catch mistyped M2M targets.
- Django's `QuerySet` typing beyond `.all()` is still thin. Keep chained queryset expressions inside the repository where you can annotate the return type as `list[SomeDTO]` and let the caller rely on that.
- Pyrefly's Django support is **actively evolving**; re-check the docs when upgrading pyrefly and remove workarounds as they become unnecessary.

## Step 9: Verify

```bash
uv run python src/manage.py check
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest
```

All five must pass. Fix any issue rather than silencing it.

## COMPLETION CHECKLIST

- [ ] Dependencies added via `uv add`
- [ ] `src/project/ids.py` with `_make_generator` helper
- [ ] `src/project/services.py` with `registry` and `get()`
- [ ] `src/project/types.py` with `AuthedRequest`
- [ ] `src/project/api/__init__.py` with `NinjaAPI` instance (per-resource routers live in `src/project/api/<resource>/` subpackages)
- [ ] Central exception handlers registered (`ValueError` → 400, `LookupError` → 404, `PermissionError` → 403)
- [ ] `src/project/signals.py` with `ReliableSignal` base
- [ ] `src/project/celery.py` + `__init__.py` export
- [ ] `urls.py` mounts `api.urls`
- [ ] Settings organized via the `settings` skill
- [ ] `pyproject.toml` has ruff / pyrefly / pytest config
- [ ] `django check`, ruff, pyrefly, pytest all pass

Once this checklist is complete, the `architecture` and `signals` skills can build features on top without any extra setup.
