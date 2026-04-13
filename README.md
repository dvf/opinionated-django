# op-django

> A collection of [Agent Skills](https://vercel.com/kb/guide/agent-skills-creating-installing-and-sharing-reusable-agent-context) that give a coding agent architectural skills to build scalable, maintainable Django projects with clean separation of concerns, testability, and a full suite of best practices.

I love Django, but some parts of it are genuinely hard to type: querysets, model instances, related managers, `F()`/`Q()` expressions, etc. In my experience, the cleanest way to handle this is to keep all the ORM work behind a repository layer that returns Pydantic DTOs. Your business logic lives in services that never import a model. Your views become one-liners, and each layer becomes very easy to mock and test.

After discussions with my friends [Haki Benita](https://github.com/hakib) and [Pete Nilson](https://github.com/petenilson), this is what I believe to be a reasonable set of patterns for flexible, testable Django projects. They're opinionated, but hold up well on large scale projects in the wild.

## A Layered Approach Using Encapsulation

Each layer encapsulates the one beneath it. The API layer never touches the ORM. Services never import a model. Repositories never leak a queryset or a model instance. Every boundary between layers is crossed as a typed Pydantic DTO, so changes stay local and tests stay fast.

```
  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │   API    │──▶│ Service  │──▶│   DTO    │──▶│   Repo   │──▶│  Model   │
  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
   thin views    business       typed data      ORM lives       
                 logic + DI     at boundaries   here only       
```

| Layer           | Role                                              | Library                                                                                          |
|-----------------|---------------------------------------------------|--------------------------------------------------------------------------------------------------|
| **API**         | Routing, input validation, OpenAPI                | [django-ninja](https://django-ninja.dev/)                                                        |
| **Service**     | Business logic & orchestration with true DI       | [svcs](https://svcs.hynek.me/)                                                                   |
| **DTO**         | Typed data at every layer boundary                | [Pydantic v2](https://docs.pydantic.dev/)                                                        |
| **Repository**  | All ORM access, transactions, prefetches          | [Django](https://www.djangoproject.com/)                                                         |
| **Model**       | Persistence with prefixed ULID primary keys       | [Django](https://www.djangoproject.com/) · [python-ulid](https://github.com/mdomke/python-ulid)  |
| **Async**       | Reliable signals & background tasks               | [Celery](https://docs.celeryq.dev/)                                                              |

## DX

| Concern                  | Tool                                                                                                                                                                                                               |
|--------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Packaging**            | [uv](https://docs.astral.sh/uv/)                                                                                                                                                                                   |
| **Settings**             | [python-decouple](https://github.com/HBNetwork/python-decouple)                                                                                                                                                    |
| **Linting & formatting** | [ruff](https://docs.astral.sh/ruff/)                                                                                                                                                                               |
| **Type checking**        | [pyrefly](https://pyrefly.org/) · [django-stubs](https://github.com/typeddjango/django-stubs)                                                                                                                      |
| **Testing**              | [pytest](https://docs.pytest.org/) · [pytest-django](https://pytest-django.readthedocs.io/) · [pytest-celery](https://docs.celeryq.dev/projects/pytest-celery/) · [freezegun](https://github.com/spulec/freezegun) |

## Install

Skills install with a single command:

```bash
# The whole collection
npx skills add dvf/opinionated-django

# Or just one
npx skills add dvf/opinionated-django/scaffold|architecture|models|services|prefixed-ulids|signals|settings|lint
```

Your agent will pick them up automatically on its next run. You can also clone the repo and point your agent at `skills/` directly.

## The Skills

Each skill is a directory under `skills/` with its own `SKILL.md`. They're designed to stand alone, but they compose nicely — `scaffold` lays the foundation, `architecture` builds features on top, and the rest fill in the details.

### 🏗️ `scaffold`
Sets up a new (or existing) Django project into the op-django layout. Creates the `src/project/` shell — `ids.py`, `services.py`, `api.py`, a `ReliableSignal` base, Celery wiring — installs dependencies with `uv`, and lays down ruff / pyrefly / pytest config. **Run this first.**

### 🔑 `prefixed-ulids`
Stripe-style prefixed ULID primary keys for every model (`prd_01jq3v...`, `ord_01jq3v...`). Time-sortable, safe to expose in URLs, debuggable in logs, and `str` end-to-end so there's no `UUID`/`str` coercion between layers.

### 🧩 `services`
Plain service classes with constructor-injected repositories, wired through an [svcs](https://svcs.hynek.me) registry. Business logic lives here, zero ORM imports allowed. Resolve anywhere — views, Celery tasks, management commands, tests — with a single generic `get[T]()` call.

### 📐 `models`
Structures Django models with `Meta` first, explicit `verbose_name`/`verbose_name_plural`, and indexes declared in `Meta.indexes` — optimized for the queries the repository actually runs. Also registers every model in the admin with a clean, fast-loading config (`list_per_page = 25`, `raw_id_fields` for large FKs, `extra = 0` on inlines).

### 🏛️ `architecture`
The full feature blueprint. Given a description, the agent scaffolds models, Pydantic DTOs, repositories, services, django-ninja routes, admin registration, and three layers of tests (repo against a real DB, service against mocked repos, API through HTTP). Every convention is spelled out; every layer is non-negotiable.

### 📡 `signals`
Reliable signals for async side-effects — notifications, cache invalidation, analytics, cross-service coordination. Receivers are enqueued **inside** the database transaction via Celery, so rollbacks are respected and delivery is at-least-once. Pattern adapted from Haki Benita's [Reliable Signals in Django](https://hakibenita.com/django-reliable-signals).

### ⚙️ `settings`
Keeps `settings.py` organized with banner-style section headers in a predictable order. Use whenever settings are added, removed, or restructured.

### 🧪 `pytest`
Three-layer pytest setup — repo against a real DB, service against mocked repos, API through HTTP — with `pytest-django`, `pytest-celery` for reliable-signal receivers, `freezegun` for time-sensitive logic, and a project `conftest.py` full of DTO factories and svcs-override fixtures.

### ✅ `lint`
Runs `ruff check`, `ruff format --check`, and `pyrefly check`, then fixes whatever it finds. Use before committing, or any time you want a clean bill of health.

## The Patterns at a Glance

- **Models** — `Meta` first (with `verbose_name`, `verbose_name_plural`, and `indexes`), prefixed ULID primary keys, indexes optimized for actual query patterns. No business logic, no custom `save()`, no properties that compute. Just fields and `__str__`.
- **DTOs** — Pydantic v2 with `from_attributes=True`. All IDs are `str`. ORM objects never leave the repository.
- **Repositories** — The only layer that touches the ORM. Returns DTOs. `@transaction.atomic` for multi-writes. One repo per aggregate root.
- **Services** — Receives dependencies via `__init__`. Pure business logic. Zero ORM imports. Testable without a database.
- **API** — django-ninja routes centralized in `project/api.py`. Input schemas are `ninja.Schema`, output schemas reuse DTOs.
- **Reliable Signals** — Side-effects enqueued inside the DB transaction via Celery. At-least-once delivery. Idempotent receivers.
- **Settings** — Sectioned with banner headers. `python-decouple` for env vars.

## Example Project

See [`example_project`](./example_project) for a working Django project built with these patterns — two apps (`products`, `orders`), full repository + service + API layering, and tests at all three levels.

## License

[MIT](./LICENSE). Use them, fork them, make them yours.
