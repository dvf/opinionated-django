# Feature Specification: Django Type Stubs

**Feature Branch**: `002-django-type-stubs`
**Created**: 2026-03-29
**Status**: Draft
**Input**: User description: "Add Python type stubs (.pyi) for common Django patterns — specifically custom extensions like request.services from the svcs middleware. ORM and models are excluded."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type-Safe Access to request.services (Priority: P1)

A developer working in a view or API handler accesses `request.services` and their IDE provides full autocomplete and type information for the `svcs.Container` methods (e.g., `.get()`). No type errors appear, and the developer can confidently use the container without consulting documentation.

**Why this priority**: This is the primary pain point — `request.services` is used in every view and API handler across the project, yet type checkers currently have no way to know it exists on `HttpRequest`.

**Independent Test**: Run the type checker against any existing view that uses `request.services` and confirm zero type errors for the `services` attribute access.

**Acceptance Scenarios**:

1. **Given** a view function that accesses `request.services`, **When** the developer runs the type checker, **Then** no errors are reported for the `services` attribute access.
2. **Given** a view function that calls `request.services.get(SomeService)`, **When** the developer hovers over `request.services` in their IDE, **Then** the type is shown as `svcs.Container`.

---

### User Story 2 - Zero-Config Stub Discovery (Priority: P2)

A new developer joins the project and writes a view that accesses `request.services`. Without any special setup beyond the standard project environment (`uv sync`), their type checker recognises the attribute and provides correct type information.

**Why this priority**: Stubs should be discoverable and automatically active — requiring manual configuration defeats the purpose.

**Independent Test**: Clone the repo fresh, run `uv sync`, open a view file, and verify that `request.services` is typed without additional configuration.

**Acceptance Scenarios**:

1. **Given** a fresh project checkout with `uv sync` completed, **When** the developer runs the type checker, **Then** the custom stubs are picked up automatically.
2. **Given** the stub files exist in the project, **When** a developer inspects the stub for `HttpRequest`, **Then** the `services: svcs.Container` attribute is clearly visible.

---

### User Story 3 - Stubs Stay In Sync with Runtime Code (Priority: P2)

When a developer modifies the middleware to change or add a new attribute on the request, the CI pipeline or local type-checking step catches any mismatch between the stub and the runtime code.

**Why this priority**: Stale stubs are worse than no stubs — they give false confidence about types.

**Independent Test**: Temporarily change the type of `request.services` in the middleware without updating the stub, run the type checker, and confirm it flags the inconsistency.

**Acceptance Scenarios**:

1. **Given** a stub declares `services: svcs.Container`, **When** the middleware is changed to assign a different type, **Then** the type checker or test suite flags the inconsistency.

---

### Edge Cases

- What happens when a developer accesses an attribute on `request` that has no stub? Standard Django `HttpRequest` typing should still apply with no regressions.
- How does the stub interact with Django REST Framework's `Request` (which wraps `HttpRequest`)? If DRF is in use, the stub should extend DRF's request type as well, or this should be documented as a known limitation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide `.pyi` type stub files that declare `request.services` as `svcs.Container` on Django's `HttpRequest`.
- **FR-002**: Type stubs MUST be automatically discovered by standard type checkers (mypy, pyright) without requiring manual configuration beyond the project's standard setup.
- **FR-003**: Type stubs MUST NOT cover Django ORM models or standard model definitions — scope is limited to custom framework-level extensions.
- **FR-004**: The project MUST include a type-checking step that validates stubs remain consistent with runtime code.
- **FR-005**: Type stubs MUST preserve all existing `HttpRequest` attributes and methods — they extend, not replace, Django's built-in types.

### Key Entities

- **Extended HttpRequest**: Django's `HttpRequest` augmented with `services: svcs.Container` via the `SvcsMiddleware`.
- **Type Stub (.pyi)**: A Python interface file that declares type information for the extended request without containing runtime logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing views and API handlers that access `request.services` pass type checking with zero errors.
- **SC-002**: Developers get accurate IDE autocomplete for `request.services` and its methods without additional setup.
- **SC-003**: A deliberate mismatch between stub and runtime code is caught by the type checker within the standard development workflow.
- **SC-004**: No regressions in type checking for standard Django `HttpRequest` attributes.

## Assumptions

- The project will adopt either `mypy` or `pyright` as its type checker (or both). Stubs will be compatible with both.
- The `svcs` library already ships with its own type information (`py.typed` or inline types).
- DRF's `Request` type handling will be addressed as a follow-up if DRF is in active use and its request type needs the same augmentation.
- Stubs will live within the project source tree (not published as a separate package).
