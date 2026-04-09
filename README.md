# op-django

A Claude Code plugin that teaches Claude a set of Django patterns I've found work well in practice.

## Why This Exists

I love Django, but some parts of it are genuinely hard to type: querysets, model instances, related managers, `F()`/`Q()` expressions. In my experience, the cleanest way to handle this is to keep all the ORM work behind a repository layer that returns Pydantic DTOs. Your business logic lives in services that never import a model. Your views become one-liners, and each layer becomes very easy to mock and test.

After a lot of back-and-forth with friends like [Haki Benita](https://github.com/hakib) and [Pete Nilson](https://github.com/petenilson), this is what I believe to be a reasonable set of patterns for flexible, testable Django projects. It's opinionated, but the opinions have been road-tested in the wild.

```
Request → View → Service → Repository → ORM
                    ↑           ↑
               pure logic   typed DTOs out, ORM stays here
```

**The stack:** uv, Django, django-ninja, Pydantic v2, svcs, python-ulid, Celery, python-decouple, ruff, pyrefly, pytest.

## What You Get

| Skill | Description |
|-------|-------------|
| `op-django:architecture` | Full feature scaffolding — models, DTOs, repos, services, routes, admin, and three-layer tests. |
| `op-django:signals` | Reliable signals (async side-effects via Celery) for post-commit work like notifications or cache invalidation. |
| `op-django:settings` | Keeps `settings.py` organized with banner-section headers. Auto-triggered when settings are modified. |
| `op-django:lint` | Runs ruff + pyrefly checks and fixes issues. |

## Install

```bash
# Add the marketplace
/plugin marketplace add dvf/op-django

# Install the plugin
/plugin install op-django
```

## Test Locally

```bash
claude --plugin-dir /path/to/op-django
```

## Example Project

See [`example_project/`](./example_project/) for a working Django project built with these patterns.

## The Patterns

- **Models** — Stripe-style prefixed ULID primary keys (`prd_01jq3v...`). No business logic in models.
- **DTOs** — Pydantic models with `from_attributes=True`. All IDs are `str`. ORM objects stay inside the repository.
- **Repositories** — The only layer that touches the ORM. Returns DTOs. `@transaction.atomic` for multi-writes.
- **Services** — Receives repos via `__init__` (true DI). Business logic only. No ORM imports.
- **Service Locator** — svcs registry with a `get()` helper. Works in views, Celery tasks, management commands — anywhere.
- **API** — django-ninja routes centralized in `project/api.py`. Input schemas are `ninja.Schema`, output schemas reuse DTOs.
- **Reliable Signals** — Side-effects enqueued inside the DB transaction via Celery. At-least-once delivery. Idempotent receivers.
- **Settings** — Sectioned with banner headers. `python-decouple` for env vars.
- **Tooling** — `uv` for everything. `ruff` for linting/formatting. `pyrefly` for type checking. `pytest` for tests.
