---
name: pytest
description: Set up and write pytest tests for an op-django project — pytest-django configuration, Celery eager mode for reliable-signal tests, freezegun for time-sensitive logic, shared conftest fixtures for DTOs and svcs overrides, and the three-layer test convention (repository against a real DB, service against mocked repos, API through HTTP). Use when adding tests to a new project, writing tests for a new feature, setting up test infrastructure, or explaining how tests should be organized.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Pytest for op-django

Testing in this project is layered the same way the code is. Each layer has its own rules, its own fixtures, and its own performance characteristics. The goal is to keep the fast tests fast — service tests should never touch a database — and to isolate the slow tests at the edges.

## The Three Layers

| File | What it covers | DB? | Speed |
|---|---|---|---|
| `test_repo.py` | ORM ↔ DTO conversion, prefetches, transactions, ID prefixes | ✅ real | slow |
| `test_service.py` | Business logic, validation, orchestration | ❌ mocked | fast |
| `test_api.py` | HTTP integration — request → view → service → repo | ✅ real | slow |

Service tests are the most valuable layer and should outnumber the others. If a service test needs `@pytest.mark.django_db`, something has leaked — find the ORM call and push it into a repository.

## Dependencies

```bash
uv add --dev pytest pytest-django pytest-celery freezegun pytest-mock
```

- **pytest-django** — the `django_db` marker, `client` fixture, settings integration.
- **pytest-celery** — lets you run Celery tasks eagerly inside tests (critical for reliable-signal receivers).
- **freezegun** — freezes `datetime.now()`, `time.time()`, and friends. Required for any logic that touches timestamps, TTLs, scheduled work, or ULIDs whose sort order matters to the test.
- **pytest-mock** — the `mocker` fixture (a thin wrapper around `unittest.mock` with autouse cleanup).

## Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "project.settings"
python_files = ["test_*.py"]
pythonpath = ["src"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]
markers = [
    "slow: deselect with '-m \"not slow\"'",
]
```

Notes:
- `pythonpath = ["src"]` is what lets `from project.services import get` resolve without an editable install.
- `--strict-markers` catches typos in `@pytest.mark.xxx`. `--strict-config` does the same for the config file.
- Keep the `markers` list small and meaningful — one or two genuine custom markers maximum.

## Celery in Tests

Reliable signals enqueue Celery tasks. For receivers to execute in-process during tests, set Celery to eager mode. Add to `src/project/settings.py` (or a test-only settings module):

```python
if "pytest" in sys.modules:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
```

With eager mode on, `send_reliable()` still goes through `transaction.on_commit`, so tests that exercise reliable signals must run inside `@pytest.mark.django_db` with `transaction=True` so `on_commit` actually fires. More on that below.

## `tests/conftest.py`

A single project-level `conftest.py` holds the fixtures every test layer can pull from. Keep it small and generic — feature-specific fixtures go in per-app `conftest.py` files.

```python
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from products.dtos.product import ProductDTO


# ---- time --------------------------------------------------------------

@pytest.fixture
def frozen_time():
    """Freeze time at a deterministic instant. Use when tests care about now()."""
    with freeze_time("2026-01-01T00:00:00Z") as frozen:
        yield frozen


# ---- svcs --------------------------------------------------------------

@pytest.fixture
def override_service():
    """
    Swap a real service factory for a fake for the duration of a test.

    Usage:
        def test_something(override_service):
            fake = MagicMock(spec=ProductService)
            fake.list_products.return_value = []
            override_service(ProductService, fake)
            ...
    """
    from project.services import registry

    originals: dict[type, Any] = {}

    def _override(service_type: type, fake: Any) -> None:
        originals.setdefault(service_type, registry._factories.get(service_type))
        registry.register_factory(service_type, lambda _container: fake)

    yield _override

    for service_type, original in originals.items():
        if original is not None:
            registry._factories[service_type] = original


# ---- DTO builders ------------------------------------------------------

@pytest.fixture
def make_product_dto():
    """Build a ProductDTO with sensible defaults; override anything via kwargs."""

    def _build(**overrides: Any) -> ProductDTO:
        fields: dict[str, Any] = {
            "id": "prd_01jq3v8f6a7b2c8d9e0f1g2h3j",
            "name": "Widget",
            "price": Decimal("9.99"),
            "stock": 5,
        }
        fields.update(overrides)
        return ProductDTO(**fields)

    return _build


# ---- repository mocks --------------------------------------------------

@pytest.fixture
def mock_product_repo(make_product_dto):
    """A MagicMock spec'd against ProductRepository, pre-loaded with a DTO."""
    from products.repositories.product import ProductRepository

    repo = MagicMock(spec=ProductRepository)
    repo.create.return_value = make_product_dto()
    repo.get_by_id.return_value = make_product_dto()
    repo.list_all.return_value = [make_product_dto()]
    return repo
```

A few patterns worth calling out:

- **Factories over fixtures for data.** `make_product_dto()` is more flexible than a `product_dto` fixture because tests can ask for `make_product_dto(stock=0)` instead of mutating a shared instance.
- **`spec=` on mocks**. Always pass `spec=SomeRepository` to `MagicMock` — it makes the mock fail fast on attribute typos and keeps tests honest when the real class changes.
- **`override_service` lets API tests substitute a fake service** without monkey-patching imports. The yield/restore dance is important so a test's override doesn't bleed into the next one.

## Writing Each Layer

### `test_repo.py` — Real database

```python
import pytest
from decimal import Decimal

from products.repositories.product import ProductRepository
from products.dtos.product import ProductDTO


@pytest.mark.django_db
def test_create_returns_dto_with_prefixed_id():
    repo = ProductRepository()

    dto = repo.create(name="Widget", price=Decimal("9.99"), stock=5)

    assert isinstance(dto, ProductDTO)
    assert dto.id.startswith("prd_")
    assert dto.price == Decimal("9.99")


@pytest.mark.django_db
def test_get_by_id_round_trips():
    repo = ProductRepository()
    created = repo.create(name="Widget", price=Decimal("9.99"), stock=5)

    fetched = repo.get_by_id(created.id)

    assert fetched == created
```

- Always assert on the **prefix** — it's a cheap proof the ULID generator is wired up.
- Assert on the **DTO type** at least once per repo — catches a repo accidentally returning an ORM instance.
- Use `@pytest.mark.django_db(transaction=True)` only when you need to exercise `transaction.on_commit` behavior (i.e. reliable-signal tests). It's significantly slower than the default.

### `test_service.py` — No database

```python
from decimal import Decimal

import pytest

from products.services.product import ProductService


def test_create_product_delegates_to_repo(mock_product_repo, make_product_dto):
    mock_product_repo.create.return_value = make_product_dto(name="Gadget")

    service = ProductService(mock_product_repo)
    result = service.create_product(name="Gadget", price=Decimal("9.99"), stock=5)

    assert result.name == "Gadget"
    mock_product_repo.create.assert_called_once_with(
        name="Gadget", price=Decimal("9.99"), stock=5
    )


def test_create_order_rejects_insufficient_stock(make_product_dto):
    order_repo = MagicMock()
    product_repo = MagicMock()
    product_repo.get_by_id.return_value = make_product_dto(stock=1)

    service = OrderService(order_repo, product_repo)

    with pytest.raises(ValueError, match="Insufficient stock"):
        service.create_order(items=[{"product_id": "prd_fake", "quantity": 5}])

    order_repo.create.assert_not_called()
```

- **No `@pytest.mark.django_db`.** If you reach for it in a service test, you've found a leak.
- Assert on **both** the return value and the repo calls. The return value proves the outcome; the call assertion proves the service routed the work correctly and didn't swallow arguments.
- Use `assert_not_called()` on negative paths — it's the cleanest way to prove that a validation error short-circuited a write.

### `test_api.py` — HTTP integration

```python
import pytest


@pytest.mark.django_db
def test_create_product(client):
    response = client.post(
        "/api/products/",
        data={"name": "Widget", "price": "9.99", "stock": 5},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("prd_")
    assert body["name"] == "Widget"


@pytest.mark.django_db
def test_list_products_empty(client):
    response = client.get("/api/products/")

    assert response.status_code == 200
    assert response.json() == []
```

- `client` is provided by pytest-django.
- Prefer asserting on **shape and a prefix** over a full dict comparison — test becomes resilient to added optional fields.
- If a route is just a passthrough to a service, one happy-path test is enough — the service tests cover the business logic, the repo tests cover persistence, and this test proves the wiring.

#### Testing the exception handler

Services raise plain Python exceptions (`ValueError`, `LookupError`, `PermissionError`); the central exception handler in `src/project/api/__init__.py` maps them to HTTP responses (400, 404, 403) with a `{"detail": "..."}` body. API tests are the layer that proves the round-trip — assert on the status code and the JSON body, not on the raised exception.

```python
@pytest.mark.django_db
def test_create_order_rejects_insufficient_stock(client):
    # Create a product with only 1 in stock.
    product_resp = client.post(
        "/products/",
        data={"name": "Limited", "price": "5.00", "stock": 1},
        content_type="application/json",
    )
    product_id = product_resp.json()["id"]

    response = client.post(
        "/orders/",
        data={"items": [{"product_id": product_id, "quantity": 10}]},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]
```

The equivalent `test_service.py` test should assert the raw exception (`with pytest.raises(ValueError, match="Insufficient stock"):`) rather than a status code — the service test doesn't go through the API, so it never sees the HTTP mapping. Layering matters: service tests prove the exception is raised, API tests prove the exception handler maps it correctly.

### Reliable-signal tests

Receivers run via Celery. With `CELERY_TASK_ALWAYS_EAGER`, they execute in-process, but `transaction.on_commit` only fires when the transaction actually commits — which means you need the `transaction=True` flavor of the marker:

```python
import pytest

from orders.receivers import on_order_created
from orders.services.order import OrderService


@pytest.mark.django_db(transaction=True)
def test_order_created_triggers_receiver(mocker, make_product_dto):
    spy = mocker.patch("orders.receivers.on_order_created", wraps=on_order_created)
    # ...build real repos, call service.create_order(...), then:
    spy.assert_called_once()


def test_receiver_is_idempotent(mocker):
    send_email = mocker.patch("orders.receivers.send_order_confirmation")

    on_order_created(order_id="ord_fake")
    on_order_created(order_id="ord_fake")

    assert send_email.call_count == 1  # or whatever idempotency you've implemented
```

The second test is the one that matters — **every receiver needs an explicit "called twice, ran once" test.** At-least-once delivery is non-negotiable and so is the test that proves you respected it.

## freezegun

Use `@freeze_time` (or the `frozen_time` fixture) for any test that asserts on timestamps, TTLs, scheduling windows, or otherwise time-sensitive logic.

```python
from freezegun import freeze_time


@freeze_time("2026-01-15T12:00:00Z")
def test_expires_at_is_24h_from_now(make_product_dto):
    service = SubscriptionService(MagicMock())
    dto = service.start_trial(user_id="usr_fake")

    assert dto.expires_at.isoformat() == "2026-01-16T12:00:00+00:00"
```

- Prefer freezing at the **test function** level, not globally — it makes the time dependency visible in the test body.
- Freeze at a **meaningful** instant (e.g. a date relevant to the assertion), not at `"2020-01-01"`. Future-you will thank you.
- Do **not** freeze time in repository tests unless the test specifically asserts on a timestamp. Frozen time interacts poorly with ULID generation, which encodes the current time into the ID.

## Common Mistakes

- **Reaching for `@pytest.mark.django_db` in a service test.** The service has an ORM import hiding in it. Fix the service, not the test.
- **Using a fixture that returns a shared mutable object.** Tests mutate it, then order-dependence bites you. Use factories (`make_*`) instead.
- **Asserting on `response.json() == {...}` with the full dict.** Too brittle. Assert on the fields you care about plus an ID prefix.
- **Forgetting `transaction=True` on reliable-signal tests.** `on_commit` won't fire, the receiver won't run, and the test silently passes without exercising anything.
- **Testing Django internals.** Don't write a test that boils down to "does `.filter()` work?" — trust the framework and test your code.
- **Missing the idempotency test.** Every reliable-signal receiver needs a test that proves calling it twice is safe.
- **Asserting on a status code for a business-rule violation in a `test_service.py` file.** Service tests should use `pytest.raises`; only `test_api.py` round-trips through the exception handler.

## Verify

```bash
uv run pytest
uv run pytest -m "not slow"       # fast loop for iterating
uv run pytest tests/orders/        # one app
uv run pytest --lf                 # re-run last failures only
```

- All tests must pass before reporting done.
- Service tests should make up the majority of the suite — if `test_repo.py` and `test_api.py` are outnumbering `test_service.py`, business logic is in the wrong layer.
