# Quickstart: Django Type Stubs

**Feature**: 002-django-type-stubs | **Date**: 2026-03-29

## Prerequisites

- Python 3.14
- uv package manager
- Project dependencies installed (`uv sync`)

## Setup

### 1. Install type checker dependencies

```bash
uv add --dev pyright django-types
```

### 2. Configure pyright

Add to `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.14"
include = ["src"]
venvPath = "."
venv = ".venv"
```

### 3. Using ServiceRequest in views

```python
# Before
from django.http import HttpRequest

def list_products(request: HttpRequest):
    repo = request.services.get(ProductRepository)  # type error!

# After
from project.types import ServiceRequest

def list_products(request: ServiceRequest):
    repo = request.services.get(ProductRepository)  # fully typed ✓
```

### 4. Run type checker

```bash
uv run pyright
```

## Verification

```bash
# Should report zero type errors for request.services access
uv run pyright src/products/api.py
uv run pyright src/orders/api.py
```
