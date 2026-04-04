# Data Model: Django Type Stubs

**Feature**: 002-django-type-stubs | **Date**: 2026-03-29

## Entities

This feature introduces no database entities. The "data model" is a type-system construct only.

### ServiceRequest

**Purpose**: Typed extension of Django's `HttpRequest` that declares the `services` attribute injected by `SvcsMiddleware`.

| Attribute | Type | Source | Notes |
|-----------|------|--------|-------|
| *(all HttpRequest attributes)* | *(inherited)* | Django | Full HttpRequest interface preserved |
| `services` | `svcs.Container` | `SvcsMiddleware` | Request-scoped DI container |

**Relationships**:
- Inherits from `django.http.HttpRequest`
- `services` attribute holds an `svcs.Container` instance scoped to the request lifecycle
- `Container.get(T)` returns `T` — generic propagation is automatic via svcs overloads

**Lifecycle**:
1. `SvcsMiddleware.__call__` creates `svcs.Container(registry)` and assigns to `request.services`
2. View/API handler accesses `request.services.get(ServiceType)` with full type inference
3. `SvcsMiddleware` closes the container in `finally` block

### No State Transitions

This is a type-only feature. No state machines, no data persistence, no migrations.
