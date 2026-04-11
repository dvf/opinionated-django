---
name: architecture
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
- `src/project/api.py` — existing routes
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

RULES:
- `CharField(max_length=64)` primary key with prefixed ULID default — NEVER UUIDs, NEVER auto-increment
- `__prefix__: ClassVar[str]` on every model
- ZERO business logic — no custom managers, no `save()` overrides, no signals, no properties that compute
- `__str__` is the only method allowed

```python
from typing import ClassVar
from django.db import models
from project.ids import generate_xxx_id

class MyEntity(models.Model):
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

ALL routes go in `src/project/api.py` — NOT in app directories.

RULES:
- Input schemas are `ninja.Schema` classes defined in `api.py`
- Output schemas reuse the DTOs from the app — do not duplicate
- Pattern: `from project.services import get`, then `get(MyEntityService)` to obtain a wired service
- `Status(code, data)` for non-200 responses
- ID path params are `str`

```python
from project.services import get

my_router = Router()

class CreateMyEntityIn(Schema):
    name: str
    # input fields...

@my_router.get("/", response=List[MyEntityDTO])
def list_entities(request):
    service = get(MyEntityService)
    return service.list_entities()

@my_router.post("/", response={201: MyEntityDTO})
def create_entity(request, payload: CreateMyEntityIn):
    service = get(MyEntityService)
    return Status(201, service.create_entity(name=payload.name))

@my_router.get("/{entity_id}/", response=MyEntityDTO)
def get_entity(request, entity_id: str):
    service = get(MyEntityService)
    return service.get_entity(entity_id)

# Mount at bottom of api.py:
api.add_router("/my-entities", my_router)
```

### Layer 8: Admin

File: `src/<app>/admin.py`

Register every model. Use `list_display` with the `id` field first. Use `TabularInline` for child models on the parent's admin.

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
- [ ] Model: `__prefix__` ClassVar, `CharField` PK with ULID default, zero logic
- [ ] DTO: `str` IDs, `from_attributes=True`, RelatedManager coercion if needed
- [ ] Repository: returns DTOs only, `model_validate()`, `@transaction.atomic` for multi-writes
- [ ] Service: repos via `__init__`, zero ORM, business logic only
- [ ] Repo and service registered in `src/project/services.py`
- [ ] Routes in `src/project/api.py` using `from project.services import get`
- [ ] Admin registered with `list_display`
- [ ] App in `INSTALLED_APPS` (if new) using dotted `AppConfig` path
- [ ] Migrations generated and applied
- [ ] `test_repo.py`: real DB, asserts ID prefix
- [ ] `test_service.py`: mocked repos, tests business logic
- [ ] `test_api.py`: HTTP integration, asserts status codes + response shape
- [ ] Signals in `src/<app>/signals.py` if async side-effects needed
- [ ] Receivers in `src/<app>/receivers.py` — idempotent, loaded in `ready()`
- [ ] `ruff check`, `ruff format --check`, `pyrefly check`, `pytest` all pass
