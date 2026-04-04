# Implementation Plan: Products and Orders Apps (e-commerce)

**Branch**: `001-setup-ecommerce` | **Date**: 2026-03-28 | **Spec**: specs/001-setup-ecommerce/spec.md
**Input**: "this is an example project containing two apps: products and orders. a fake ecommerce site."

## Summary

This feature establishes the core of a fake e-commerce site with two Django apps: `products` and `orders`. We will implement the Repository pattern with Pydantic DTOs and `svcs` dependency injection, ensuring lean models and full type safety.

## Technical Context

**Language/Version**: Python 3.12 (standard for modern projects)
**Primary Dependencies**: Django 4.2+, Pydantic v2, svcs, uv
**Storage**: SQLite (default for initial dev/setup)
**Testing**: pytest-django (standard for Django projects)
**Target Platform**: Linux/Darwin
**Project Type**: Django Web Application (API-first)
**Performance Goals**: Fast repository operations (<100ms)
**Constraints**: MUST use Repository pattern, Pydantic DTOs, and svcs DI.
**Scale/Scope**: MVP with two core apps: Products and Orders.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Dependency Injection (svcs)**: ✅ Planning to use `svcs` container in views/services.
- **Repository Pattern**: ✅ All data access via repository classes.
- **Typed Data Transfer (Pydantic)**: ✅ Repositories will return Pydantic models.
- **Lean Django Models**: ✅ Business logic in services, models for schema only.
- **Modern Execution Environment (uv)**: ✅ `uv` will be used for environment setup.

## Project Structure

### Documentation (this feature)

```text
specs/001-setup-ecommerce/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── products/            # Django app for products
│   ├── models/          # Lean Django models
│   ├── repositories/    # Product repositories returning DTOs
│   ├── services/        # Product business logic
│   └── dtos/            # Pydantic schemas
├── orders/              # Django app for orders
│   ├── models/          # Lean Django models
│   ├── repositories/    # Order repositories returning DTOs
│   ├── services/        # Order business logic
│   └── dtos/            # Pydantic schemas
├── project/             # Project config, API, svcs setup
└── manage.py
```

**Structure Decision**: Multi-app Django project following the principle-mandated repository and service layers.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
