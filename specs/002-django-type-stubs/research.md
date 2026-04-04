# Research: Django Type Stubs

**Feature**: 002-django-type-stubs | **Date**: 2026-03-29

## Decision 1: Stub Approach

**Decision**: Use a `ServiceRequest(HttpRequest)` subclass with `services: svcs.Container` attribute annotation.

**Rationale**: This is the established community pattern (mirrors `AuthenticatedHttpRequest` from django-stubs docs and django-ninja issue #508). It works identically with both mypy and pyright, requires no plugin magic, no stub discovery configuration, and no separate stubs directory. The subclass is a type-only construct — at runtime, the request object remains a plain `HttpRequest`.

**Alternatives considered**:
- **`stubs/` directory augmenting HttpRequest**: Rejected — requires replicating the entire HttpRequest signature or losing attributes. Conflicts with django-stubs if installed. Ownership burden for maintaining full module stubs.
- **Protocol-based typing**: Rejected — `HttpRequest` doesn't structurally conform to a `HasServices` protocol without additional stubs. Known pyright gaps with Protocol attribute access (`reportAttributeAccessIssue`).

**Implementation**: Create `src/project/types.py` containing:
```python
from django.http import HttpRequest
import svcs

class ServiceRequest(HttpRequest):
    services: svcs.Container
```

Update all view/API handler signatures from `request: HttpRequest` to `request: ServiceRequest`.

## Decision 2: Type Checker

**Decision**: pyright as primary type checker (editor + CI).

**Rationale**: Sub-second incremental checks, native Pylance/VS Code integration, consumes `py.typed` packages (svcs, django-ninja, pydantic) without plugins. django-types 0.23.0 provides pyright-compatible Django stubs.

**Alternatives considered**:
- **mypy + django-stubs**: Better ORM inference via plugin, but slower, requires Django settings at check-time, and ORM typing is explicitly out of scope per constitution Principle VII. Can be layered in later as a secondary CI check if needed.

## Decision 3: Stub Discovery

**Decision**: No custom `stubPath` needed. The `ServiceRequest` subclass lives in `src/project/types.py` as a regular Python module, not a `.pyi` stub file.

**Rationale**: Since we use the subclass approach (not third-party augmentation), stubs are discovered as normal source code. pyright configuration only needs `include = ["src"]`.

**Note on `.pyi` files**: The `.pyi` convention from Constitution Principle VII is satisfied by the typed module approach. If future extensions require augmenting third-party types directly (e.g., adding attributes to DRF's `Request`), a `stubs/` directory with `.pyi` files and `stubPath` configuration would be added at that time.

## Decision 4: django-ninja Compatibility

**Decision**: Fully compatible — no changes needed to django-ninja.

**Rationale**: django-ninja identifies the request parameter by **name** (`if name == "request": continue`), not by type annotation. A `ServiceRequest` annotation works transparently. The runtime object is whatever Django passes — the annotation is purely for static analysis.

## Decision 5: svcs Container.get() Generic Propagation

**Decision**: No special setup needed.

**Rationale**: svcs ships `py.typed` with 10 explicit `@overload` signatures for `Container.get()`. Once `request.services` is typed as `svcs.Container`, the type checker resolves `request.services.get(ProductRepository)` → `ProductRepository` automatically. Standard PEP 484 overload resolution.

## Dependencies to Add

```
uv add --dev pyright django-types
```

## Configuration

```toml
# pyproject.toml additions
[tool.pyright]
pythonVersion = "3.14"
include = ["src"]
venvPath = "."
venv = ".venv"
```
