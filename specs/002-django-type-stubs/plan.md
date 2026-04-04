# Implementation Plan: Django Type Stubs

**Branch**: `002-django-type-stubs` | **Date**: 2026-03-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-django-type-stubs/spec.md`

## Summary

Add `.pyi` type stub files so that `request.services` (a `svcs.Container` injected by `SvcsMiddleware`) is recognized by type checkers and IDEs. Introduce a type checker (pyright) into the project toolchain, configure it to discover custom stubs, and ensure stubs stay in sync via CI/type-checking step.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Django 6.0.3, django-ninja 1.6.2, svcs 25.1.0, Pydantic v2
**Storage**: SQLite (dev), N/A for this feature
**Testing**: pytest + pytest-django
**Target Platform**: Linux/macOS server
**Project Type**: Web service (Django + django-ninja API)
**Performance Goals**: N/A (developer tooling feature)
**Constraints**: Stubs must work with pyright and mypy; zero runtime overhead
**Scale/Scope**: 2 Django apps (products, orders), ~44 source files, 4 views/API handlers using `request.services`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Dependency Injection (svcs) | PASS | Feature enhances DI by making `svcs.Container` on request type-safe |
| II. Repository Pattern | PASS | No changes to repository layer |
| III. Typed Data Transfer (Pydantic) | PASS | No changes to DTOs |
| IV. Lean Django Models | PASS | No model changes |
| V. Modern Execution Environment (uv) | PASS | Type checker will be added as a uv dependency |
| VI. Code Quality and Formatting (ruff) | PASS | Stubs will pass ruff checks |
| VII. Type Stubs for Django Extensions (.pyi) | PASS | This feature directly implements this principle |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-django-type-stubs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── project/
│   ├── middleware.py     # SvcsMiddleware (existing, add type annotations)
│   └── types.py          # NEW: ServiceRequest(HttpRequest) with services: svcs.Container
├── products/
│   ├── api.py            # Update: HttpRequest → ServiceRequest
│   └── views/product.py  # Update: HttpRequest → ServiceRequest
└── orders/
    ├── api.py            # Update: HttpRequest → ServiceRequest
    └── views/order.py    # Update: HttpRequest → ServiceRequest

pyproject.toml              # Update: add [tool.pyright] config, dev deps
```

**Structure Decision**: `ServiceRequest` subclass in `src/project/types.py` (regular Python module, not a `.pyi` stub file). Research confirmed this is the standard pattern — no separate `stubs/` directory needed. pyright config lives in `pyproject.toml`.

## Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Dependency Injection (svcs) | PASS | ServiceRequest makes svcs.Container type-safe on request |
| II. Repository Pattern | PASS | No repository changes |
| III. Typed Data Transfer (Pydantic) | PASS | No DTO changes |
| IV. Lean Django Models | PASS | No model changes |
| V. Modern Execution Environment (uv) | PASS | pyright + django-types added via `uv add --dev` |
| VI. Code Quality and Formatting (ruff) | PASS | New files will pass ruff |
| VII. Type Stubs for Django Extensions (.pyi) | PASS | ServiceRequest subclass + pyright implements this principle. Research confirmed subclass approach is the standard pattern — `.pyi` stubs reserved for third-party augmentation if needed later |

**Post-design gate result**: PASS — no violations.

## Complexity Tracking

No constitution violations — table not applicable.
