# future-django Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-01

## Active Technologies

- Python 3.14 + Django 6.0.3, django-ninja 1.6.2, svcs 25.1.0, Pydantic v2, python-ulid 3.1.0

## Project Structure

```text
src/
  project/    # Django project config, API, svcs setup, ID generation
  products/   # Products app
  orders/     # Orders app
tests/
specs/
```

## Commands

```bash
uv run pytest              # run tests
uv run ruff check src      # lint
```

## ID Strategy

All models use Stripe-style prefixed ULID primary keys (`<prefix>_<ulid>`). Prefixes are 3-4 chars. Generators live in `src/project/ids.py`. Never use UUIDs or auto-incrementing integers.

## Code Style

Python 3.14: Follow standard conventions

## Recent Changes

- Stripe-style prefixed ULID IDs replacing UUID primary keys
- Renamed `core/` → `project/`
- Consolidated API routes into `project/api.py`
- 002-django-type-stubs: Added Python 3.14 + Django 6.0.3, django-ninja 1.6.2, svcs 25.1.0, Pydantic v2

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
