<!--
Sync Impact Report
- Version change: [PROJECT_NAME] Constitution v0.0.0 (template) -> v1.0.0
- List of modified principles:
  - PRINCIPLE_1: [PRINCIPLE_1_NAME] -> Dependency Injection (svcs)
  - PRINCIPLE_2: [PRINCIPLE_2_NAME] -> Repository Pattern
  - PRINCIPLE_3: [PRINCIPLE_3_NAME] -> Typed Data Transfer (Pydantic)
  - PRINCIPLE_4: [PRINCIPLE_4_NAME] -> Lean Django Models
  - PRINCIPLE_5: [PRINCIPLE_5_NAME] -> Modern Execution Environment (uv)
- Added sections: Technology Stack, Testing Standards
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

## Technology Stack

The project is built on a modern Python stack:
- **Framework**: Django 4.2+
- **Dependency Injection**: `svcs`
- **Data Validation/DTOs**: Pydantic v2
- **Package Management**: `uv`

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

**Version**: 1.0.0 | **Ratified**: 2026-03-28 | **Last Amended**: 2026-03-28
