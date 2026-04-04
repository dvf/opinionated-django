<!--
Sync Impact Report
- Version change: future-django Constitution v1.1.0 -> v1.2.0
- List of modified principles:
  - PRINCIPLE_1: Dependency Injection (svcs) (unchanged)
  - PRINCIPLE_2: Repository Pattern (unchanged)
  - PRINCIPLE_3: Typed Data Transfer (Pydantic) (unchanged)
  - PRINCIPLE_4: Lean Django Models (unchanged)
  - PRINCIPLE_5: Modern Execution Environment (uv) (unchanged)
  - PRINCIPLE_6: Code Quality and Formatting (ruff) (unchanged)
  - PRINCIPLE_7: Stripe-style Prefixed ULID Identifiers (NEW)
  - PRINCIPLE_8: Type Stubs for Django Extensions (.pyi) (renumbered from VII)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (aligned)
  - ✅ .specify/templates/spec-template.md (aligned)
  - ✅ .specify/templates/tasks-template.md (aligned)
- Follow-up TODOs: None
-->

# future-django Constitution

## Core Principles

### I. Dependency Injection (svcs)
Mandatory use of the `svcs` library for dependency injection. Components MUST NOT instantiate their dependencies directly; they must request them from the `svcs` container. This ensures all components are easily mockable and swappable for testing, promoting loose coupling across the application.

### II. Repository Pattern
All data access MUST be encapsulated within a Repository layer. Repositories isolate the application from the underlying database schema and Django ORM complexities. This allows for easier testing with in-memory implementations and ensures a clear boundary for data persistence logic.

### III. Typed Data Transfer (Pydantic)
Repositories MUST return Pydantic models (DTOs) rather than Django ORM models to the service and view layers. This provides full type safety, automatic validation, and prevents ORM objects from "leaking" into layers where they don't belong, avoiding the common pitfalls of untyped Django code.

### IV. Lean Django Models
Django models MUST be kept "thin," restricted to schema definitions and basic persistence logic. All business rules, complex validations, and domain logic MUST reside in the Service layer. This prevents the "fat model" anti-pattern and keeps the domain logic decoupled from the database structure.

### V. Modern Execution Environment (uv)
The project MUST use `uv` for all dependency management and application execution. This ensures fast, reliable, and reproducible development and deployment environments across all team members and CI/CD pipelines.

### VI. Code Quality and Formatting (ruff)
The project MUST use `ruff` for linting, formatting, and import organization. All code MUST pass `ruff check` and `ruff format` before being considered complete. This ensures a consistent style, optimized imports, and prevents common errors across the codebase.

### VII. Stripe-style Prefixed ULID Identifiers
All models MUST use Stripe-style prefixed ULID strings as primary keys (e.g. `prd_01jq3v...`). Each model declares a `__prefix__` class variable and uses a `CharField(max_length=64)` primary key with a generated default from `project.ids`. UUIDs and auto-incrementing integers are prohibited. New entity prefixes must be short (3-4 chars) and registered in `project.ids`. IDs are opaque strings throughout the stack — DTOs, repositories, services, and API endpoints all use `str`, never `UUID`.

### VIII. Type Stubs for Django Extensions (.pyi)
The project MUST maintain `.pyi` type stub files for custom extensions to Django's standard types. This applies to patterns where the project adds attributes or methods to Django objects that type checkers cannot infer (e.g., `request.services` added by `SvcsMiddleware`). ORM models and standard Django model definitions are explicitly excluded — stubs are only required for custom middleware augmentations, custom request/response attributes, and similar framework-level extensions. Stubs MUST be kept in sync with their corresponding runtime code and verified by the project's type checker.

## Technology Stack

The project is built on a modern Python stack:
- **Framework**: Django 6.0+
- **Dependency Injection**: `svcs`
- **Data Validation/DTOs**: Pydantic v2
- **Package Management**: `uv`
- **Linting & Formatting**: `ruff`

## Testing Standards

- **TDD (Test-Driven Development)**: New features MUST be developed using a TDD approach.
- **Independence**: Each user story MUST be independently testable.
- **Layered Testing**: Unit tests for services/repos, contract tests for APIs, and integration tests for full user journeys.

## Governance

- **Supremacy**: This constitution takes precedence over all other architectural practices in the project.
- **Amendments**:
  - **MAJOR**: Backward incompatible governance/principle removals or redefinitions.
  - **MINOR**: New principles or significantly expanded guidance.
  - **PATCH**: Clarifications, wording, or non-semantic refinements.
- **Review**: Every implementation plan MUST include a "Constitution Check" to verify alignment.

**Version**: 1.2.0 | **Ratified**: 2026-03-28 | **Last Amended**: 2026-04-01
