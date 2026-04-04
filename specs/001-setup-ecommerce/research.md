# Research: Products and Orders (e-commerce)

## Overview

The architectural challenge here is to integrate the Repository pattern and `svcs` dependency injection into a Django framework while maintaining high performance and type safety.

## Decision 1: svcs Integration in Django

- **Decision**: Use a middleware to initialize the `svcs` container per request.
- **Rationale**: This allows easy access to the container in views and ensures that resources are correctly closed at the end of the request.
- **Alternatives considered**: 
  - Manual container management in each view: Rejected for being boilerplate-heavy and error-prone.
  - Global container: Rejected due to potential thread-safety and resource leakage issues.

## Decision 2: Repository Pattern Implementation

- **Decision**: Repositories will receive a database connection or a Django manager via `svcs`.
- **Rationale**: Keeps repositories decoupled from the global Django ORM state and facilitates unit testing with in-memory databases or mocks.
- **Alternatives considered**:
  - Direct ORM access in repositories: Rejected as it binds repositories too tightly to the Django framework's global state.

## Decision 3: Pydantic DTO Mapping

- **Decision**: Use Pydantic's `model_validate(obj, from_attributes=True)` to map Django ORM objects to DTOs in the repository layer.
- **Rationale**: It's efficient, type-safe, and provides a clear separation between the database and the domain.
- **Alternatives considered**:
  - Manual mapping: Rejected for being verbose and hard to maintain.

## Decision 4: uv and Project Setup

- **Decision**: Use `uv init` followed by adding `django`, `pydantic`, `svcs` as dependencies.
- **Rationale**: `uv` provides a fast and reliable environment, matching our constitutional mandate.
- **Alternatives considered**:
  - `pip` / `venv`: Rejected in favor of modern tooling.

## Best Practices

- **Testing**: Use `pytest-django` and `pytest-mock`. Test repositories independently of Django's database if possible (e.g., using sqlite in-memory for speed).
- **Typing**: Use `mypy` for static analysis to ensure Pydantic DTOs and repository contracts are correctly typed throughout the application.
