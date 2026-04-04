# Quickstart: Products and Orders

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed.
- Python 3.12+

## Setup

1. Initialize project and install dependencies:
   ```bash
   uv init
   uv add django pydantic svcs pytest-django ruff
   ```
2. Initialize Django project:
   ```bash
   uv run django-admin startproject project .
   uv run python manage.py startapp products
   uv run python manage.py startapp orders
   ```
3. Run migrations:
   ```bash
   uv run python manage.py migrate
   ```

## Development

1. Follow the Repository and Service patterns defined in the constitution.
2. Ensure `svcs` is configured via middleware in `project/settings.py`.
3. Map repositories to `svcs` in `project/services.py`.

## Testing

Run tests with `pytest`:
```bash
uv run pytest
```
