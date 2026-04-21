---
name: dj-architecture
description: Implement a Django feature following the opinionated architecture — prefixed ULID IDs, repository pattern, Pydantic DTOs, svcs service locator, project-scoped django-ninja API, Celery reliable signals, and layered tests. Use when the user asks to add a new entity, endpoint, app, or business logic in a Django project that follows these conventions.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Implement a Django Feature

You are implementing a feature in an opinionated, fully type-safe Django project managed with `uv`. Every convention below is mandatory. Do not deviate.

**Why this architecture exists:** Django's ORM is powerful but hard to type — querysets, model instances, related managers, and `F()`/`Q()` expressions don't play well with static type checkers. This project solves that by pushing all ORM usage into repositories that return Pydantic DTOs. Services receive repos via constructor injection and contain pure business logic with zero ORM imports. Views are thin dispatchers. The result: everything from the repository boundary outward is fully typed, IDE-friendly, and testable in isolation.

**Tooling:** `uv` is the package manager. All commands use `uv run`. Never use `pip`, `poetry`, or raw `python` — always `uv run python`, `uv run pytest`, etc. To add a dependency: `uv add <package>`.

## BEFORE WRITING CODE

Gather current project state by reading:

- `src/project/ids.py` — existing ID prefixes (must be unique)
- `src/project/services.py` — registered repos/services
- `src/project/settings.py` — `INSTALLED_APPS`
- `src/project/api/__init__.py` — `NinjaAPI()`, mounted resource routers, exception handlers
- `src/project/api/<resource>/` — existing per-resource route packages
- `src/project/types.py` — `AuthedRequest` and other shared request types
- `ARCHITECTURE.md` if present — full pattern reference
- Any existing app the feature touches

Then state your implementation plan: models, DTOs, repos, services, routes, tests, and ID prefixes.

---

## LAYER-BY-LAYER IMPLEMENTATION

Follow this exact order. Do not skip layers. Each layer has rules that are non-negotiable.

### Layer 1: ID Generator

Add to `src/project/ids.py`:

```python
generate_xxx_id = _make_generator("xxx")  # 3-4 char prefix
```

Prefixes must be unique across the project and short enough to be readable in logs.

### Layer 2: Model

File: `src/<app>/models/<entity>.py`

Follow the **models** skill for full conventions. The key rules:

- `class Meta` is **always first** inside the model body — with `verbose_name`, `verbose_name_plural`, and `indexes`
- `CharField(max_length=64)` primary key with prefixed ULID default — NEVER UUIDs, NEVER auto-increment
- `__prefix__: ClassVar[str]` on every model
- All indexes in `Meta.indexes` — never `db_index=True` on fields. Optimize for queries the repository actually runs.
- ZERO business logic — no custom managers, no `save()` overrides, no signals, no properties that compute
- `__str__` is the only method allowed

```python
from typing import ClassVar
from django.db import models
from project.ids import generate_xxx_id

class MyEntity(models.Model):
    class Meta:
        verbose_name = "my entity"
        verbose_name_plural = "my entities"
        indexes = [
            models.Index(fields=["created_at"], name="idx_%(class)s_created"),
        ]

    __prefix__: ClassVar[str] = "xxx"
    id = models.CharField(max_length=64, primary_key=True, default=generate_xxx_id, editable=False)
    # fields...
    def __str__(self):
        return self.name
```

If this is a new app, add it to `INSTALLED_APPS` in `src/project/settings.py` using the dotted path to its `AppConfig` (e.g., `"myapp.apps.MyAppConfig"`).

Then run:
```bash
uv run python src/manage.py makemigrations && uv run python src/manage.py migrate
```

### Layer 3: DTO

File: `src/<app>/dtos/<entity>.py`

RULES:
- ALL ID fields are `str` — never `UUID`
- `model_config = ConfigDict(from_attributes=True)` — always
- For Django `RelatedManager` fields (reverse FKs, M2M), add the coercion validator:

```python
@field_validator("children", mode="before")
@classmethod
def coerce_related_manager(cls, v):
    if hasattr(v, "all"):
        return list(v.all())
    return v
```

### Layer 4: Repository

File: `src/<app>/repositories/<entity>.py`

RULES:
- ORM objects NEVER leave this layer — every public method returns a DTO or `list[DTO]`
- Convert with `MyEntityDTO.model_validate(orm_obj)`
- `prefetch_related()` when the DTO has nested relations
- `@transaction.atomic` on any method with multiple writes
- One repo per aggregate root — child entities are managed by the parent's repo
- All ID params are `str`

### Layer 5: Service

File: `src/<app>/services/<entity>.py`

RULES:
- Receives repos via `__init__` — NEVER instantiates them, NEVER imports models
- Contains all business logic: validation, orchestration, cross-repo coordination
- Touches ZERO ORM — no `.objects`, no `F()`, no `Q()`, no model imports
- Returns DTOs

### Layer 6: Register in svcs

Add to `src/project/services.py`:

```python
from myapp.repositories.my_entity import MyEntityRepository
from myapp.services.my_entity import MyEntityService

# Register the repository
registry.register_factory(MyEntityRepository, MyEntityRepository)

# Register the service with a factory that pulls its repo dependencies
def _my_entity_service_factory(container: svcs.Container) -> MyEntityService:
    repo = container.get(MyEntityRepository)
    return MyEntityService(repo)

registry.register_factory(MyEntityService, _my_entity_service_factory)
```

Both repos and services get registered. Service factories wire up repo dependencies via the container. The `get()` helper at the bottom of the file makes them available anywhere.

### Layer 7: API Routes

Routes live in a per-resource package under `src/project/api/` — NOT in app directories. Each resource is its own subpackage:

```
src/project/
└── api/
    ├── __init__.py          # NinjaAPI(), exception handlers, mounts routers
    ├── my_entities/
    │   ├── __init__.py      # re-exports `router` from routes
    │   ├── routes.py        # handlers
    │   └── schemas.py       # ninja.Schema input models
    └── other_resource/
        ├── __init__.py
        ├── routes.py
        └── schemas.py
```

RULES:
- Input schemas are `ninja.Schema` classes defined in `schemas.py` next to the routes
- Output schemas reuse the DTOs from the app — do not duplicate
- The resource package's `__init__.py` re-exports the `router` from `routes` (e.g. `from .routes import router`)
- The top-level `src/project/api/__init__.py` creates the `NinjaAPI()` instance, registers exception handlers, and mounts each resource router with `api.add_router("/my-entities", my_entities_router)`
- Pattern: `from project.services import get`, then `get(MyEntityService)` to obtain a wired service
- Every handler's first arg is typed `request: AuthedRequest` — never untyped. `AuthedRequest` lives in `src/project/types.py` and narrows `request.user` to an authenticated Django `User`
- ID path params are `str`
- Handlers do NOT try/except — errors bubble up to the central exception handler (see below)

`src/project/api/my_entities/routes.py`:

```python
from typing import List

from ninja import Router, Status

from myapp.dtos.my_entity import MyEntityDTO
from myapp.services.my_entity import MyEntityService
from project.services import get
from project.types import AuthedRequest

from .schemas import CreateMyEntityIn

router = Router()


@router.get("/", response=List[MyEntityDTO])
def list_entities(request: AuthedRequest):
    return get(MyEntityService).list_entities()


@router.post("/", response={201: MyEntityDTO})
def create_entity(request: AuthedRequest, payload: CreateMyEntityIn):
    return Status(201, get(MyEntityService).create_entity(name=payload.name))


@router.get("/{entity_id}/", response=MyEntityDTO)
def get_entity(request: AuthedRequest, entity_id: str):
    return get(MyEntityService).get_entity(entity_id)
```

#### Central exception handlers

Services raise plain Python exceptions — `ValueError` for bad input, `LookupError` for missing records, `PermissionError` for forbidden access. They do NOT know about HTTP. The mapping happens once, centrally, in `src/project/api/__init__.py`:

- `ValueError` → `400 {"detail": str(exc)}`
- `LookupError` → `404 {"detail": str(exc)}`
- `PermissionError` → `403 {"detail": str(exc)}`

```python
@api.exception_handler(ValueError)
def on_value_error(request, exc: ValueError):
    return api.create_response(request, {"detail": str(exc)}, status=400)
```

Route handlers MUST NOT wrap service calls in try/except — errors bubble up and the central handler turns them into responses.

### Layer 8: Admin

File: `src/<app>/admin.py`

Follow the **models** skill for full admin conventions. The key rules:

- Register every model with `@admin.register`
- `list_display` — `id` first, then 3-5 most useful columns
- `list_per_page = 25` — keeps the admin fast on large tables
- `search_fields` — always include `id`, plus name/title fields
- `readonly_fields` — always include `id` (ULID PKs are never edited)
- `ordering` — explicit, usually `-created_at` or the primary time field
- `list_select_related` — specify FKs shown in `list_display` to avoid N+1s
- `raw_id_fields` or `autocomplete_fields` for FKs to large tables
- `TabularInline` for child models — `extra = 0`, `show_change_link = True`

---

## TESTS

Write three test layers in `tests/<app>/`. No test file may be skipped.

### `test_repo.py` — Real database, validate ORM ↔ DTO conversion

```python
@pytest.mark.django_db
def test_create_and_get():
    repo = MyEntityRepository()
    dto = repo.create(name="Test", ...)
    assert isinstance(dto, MyEntityDTO)
    assert dto.id.startswith("xxx_")
    fetched = repo.get_by_id(dto.id)
    assert fetched == dto

@pytest.mark.django_db
def test_list_all():
    repo = MyEntityRepository()
    repo.create(name="A", ...)
    repo.create(name="B", ...)
    assert len(repo.list_all()) == 2
```

### `test_service.py` — Mock the repos, validate business logic

Services are tested WITHOUT a database. Mock the repository. This is the most important test layer — it proves your business logic is correct independently of Django.

```python
from unittest.mock import MagicMock

def test_create_delegates_to_repo():
    repo = MagicMock()
    expected = MyEntityDTO(id="xxx_fake", name="Test", ...)
    repo.create.return_value = expected

    service = MyEntityService(repo)
    result = service.create_entity(name="Test", ...)

    assert result == expected
    repo.create.assert_called_once_with(name="Test", ...)

def test_business_rule_rejects_bad_input():
    repo = MagicMock()
    # configure mock to trigger the rule
    service = MyEntityService(repo)

    with pytest.raises(ValueError, match="..."):
        service.do_something_invalid(...)
```

### `test_api.py` — Integration through HTTP

```python
@pytest.mark.django_db
def test_create(client):
    resp = client.post("/my-entities/", data={...}, content_type="application/json")
    assert resp.status_code == 201
    assert resp.json()["id"].startswith("xxx_")

@pytest.mark.django_db
def test_list_empty(client):
    resp = client.get("/my-entities/")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.django_db
def test_get_by_id(client):
    create_resp = client.post("/my-entities/", data={...}, content_type="application/json")
    eid = create_resp.json()["id"]
    resp = client.get(f"/my-entities/{eid}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == eid
```

---

## RELIABLE SIGNALS (CELERY)

When a business operation needs to trigger async side-effects (notifications, cache invalidation, analytics), use reliable signals — NOT standard Django signals.

### Signal Definition

File: `src/<app>/signals.py`

```python
from project.signals import ReliableSignal

my_event = ReliableSignal()
```

### Sending

Call `send_reliable()` **inside** a `transaction.atomic()` block in the service layer. Arguments MUST be JSON-serializable — pass entity IDs, never model instances:

```python
# In the service method
def create_entity(self, name: str) -> MyEntityDTO:
    with transaction.atomic():
        entity = self.repo.create(name=name)
        my_event.send_reliable(sender=None, entity_id=entity.id)
    return entity
```

### Receivers

File: `src/<app>/receivers.py`

Register with `@receiver`. Load receivers in `apps.py` → `ready()`.

**CRITICAL: Every receiver MUST be idempotent.** The system guarantees at-least-once delivery, not exactly-once. A receiver may run more than once for the same event. Design accordingly:

- Check if the action was already performed before performing it
- Use database constraints or flags to prevent duplicate effects
- Never assume a receiver runs exactly once

```python
from django.dispatch import receiver
from .signals import my_event

@receiver(my_event)
def on_my_event(obj_id: str, **kwargs):
    # Idempotent: guard against duplicate execution
    if already_processed(obj_id):
        return
    do_work(obj_id)
```

### apps.py

```python
class MyAppConfig(AppConfig):
    def ready(self):
        from . import receivers  # noqa: F401
```

### Testing Receivers

Test receivers in isolation. Mock external dependencies. Verify idempotency by calling the receiver twice with the same arguments:

```python
def test_receiver_is_idempotent():
    on_my_event(obj_id="xxx_fake")
    on_my_event(obj_id="xxx_fake")  # second call must be safe
    # assert side-effect happened exactly once
```

### RULES

- NEVER use standard `send()` for post-commit side-effects — use `send_reliable()`
- Arguments MUST be JSON-serializable (strings, numbers, booleans)
- Receivers MUST be idempotent — this is non-negotiable
- Receivers MUST NOT import or touch ORM models directly — use a repository if DB access is needed

---

## Module Size Limits

Every Python module has a soft and hard line budget. These limits force the repo → service → API layers to stay thin and focused — when a file outgrows them, it's almost always because a concern has crept across layers.

| Limit | Value | Action |
|---|---|---|
| Soft | **200 lines** | Review for split at next touch. Not a blocker. |
| Hard | **400 lines** | MUST be split before merging further growth. |

When a module exceeds the hard limit OR covers more than one concern, convert it to a package directory with one file per concern, re-exported via `__init__.py`:

```
# Before
<app>/tasks.py         # 500+ lines, many unrelated tasks

# After
<app>/tasks/
  __init__.py          # re-exports public tasks
  billing.py           # billing-related @shared_task definitions
  notifications.py     # notification tasks
  ingestion.py         # ingestion tasks
```

External imports don't change: `from myapp.tasks import charge_customer` works the same before and after.

### Exemptions

Four categories are exempt from the line limit:

1. **`**/migrations/*.py`** — Django auto-generates these; never hand-edit.
2. **Fixture data files** — pure test data (large `FIXTURE = [...]` blocks) in `tests/fixtures/data/` or named `*_data.py`. Data is not code.
3. **Generated code** — protobuf, GraphQL schemas, OpenAPI clients, etc. Document the generator in a comment at the top.
4. **Third-party / vendored code** — shouldn't modify anyway.

### NOT exempt

Some common "surely this is special" cases that are NOT exempt:

- **Test files.** A 500-line `test_foo.py` is a bad smell — split by concern (`test_create.py`, `test_update.py`, `test_permissions.py`).
- **`conftest.py`.** If it grows past 400 lines, move fixtures into `tests/fixtures/*.py` modules and have `conftest.py` re-export them.
- **Re-export `__init__.py`.** If it grows past 200 lines, the package has too much public surface — refactor the package, don't exempt the file.
- **`tasks.py` / `services.py` / `forms.py`.** Split to a directory (rule above). Do not exempt.

`models/`, `admin/`, and API router directories are already mandatorily-directory from day one under separate skills — those don't hit the size limit because they split per-entity from the start.

---

## VERIFY

Run all four checks. ALL must pass before you report done.

```bash
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest
```

If anything fails, fix it and re-run.

---

## COMPLETION CHECKLIST

Before reporting done, confirm every item:

- [ ] ID generator in `src/project/ids.py` with unique 3-4 char prefix
- [ ] Model: `Meta` first (verbose names + indexes), `__prefix__` ClassVar, `CharField` PK with ULID default, zero logic
- [ ] DTO: `str` IDs, `from_attributes=True`, RelatedManager coercion if needed
- [ ] Repository: returns DTOs only, `model_validate()`, `@transaction.atomic` for multi-writes
- [ ] Service: repos via `__init__`, zero ORM, business logic only
- [ ] Repo and service registered in `src/project/services.py`
- [ ] Routes in `src/project/api/<resource>/routes.py`, schemas in `schemas.py`, mounted in `src/project/api/__init__.py` using `from project.services import get`
- [ ] `request: AuthedRequest` annotation on every handler
- [ ] Central exception handlers registered in `src/project/api/__init__.py` (`ValueError`→400, `LookupError`→404, `PermissionError`→403)
- [ ] Admin registered per **models** skill conventions (`list_display`, `list_per_page = 25`, `search_fields`, `readonly_fields`, `ordering`, `raw_id_fields`/`autocomplete_fields` for large FKs, inlines with `extra = 0`)
- [ ] App in `INSTALLED_APPS` (if new) using dotted `AppConfig` path
- [ ] Migrations generated and applied
- [ ] `test_repo.py`: real DB, asserts ID prefix
- [ ] `test_service.py`: mocked repos, tests business logic
- [ ] `test_api.py`: HTTP integration, asserts status codes + response shape
- [ ] Signals in `src/<app>/signals.py` if async side-effects needed
- [ ] Receivers in `src/<app>/receivers.py` — idempotent, loaded in `ready()`
- [ ] `ruff check`, `ruff format --check`, `pyrefly check`, `pytest` all pass
