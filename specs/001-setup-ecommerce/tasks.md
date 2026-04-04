# Tasks: Products and Orders Apps

**Input**: Design documents from `specs/001-setup-ecommerce/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Initialize project with `uv init`
- [X] T002 [P] Add dependencies: django, pydantic, svcs, pytest-django using `uv add`
- [X] T003 Initialize Django project `project` and apps `products`, `orders` in `src/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Configure `svcs` middleware in `src/project/settings.py`
- [X] T005 Setup `svcs` container and registry in `src/project/services.py`
- [X] T006 [P] Configure database and run initial migrations in `src/manage.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Product Management (Priority: P1) 🎯 MVP

**Goal**: Manage a catalog of products so that customers can browse and purchase items.

**Independent Test**: Create a product through a repository and verify it can be retrieved by ID as a typed Pydantic object.

### Tests for User Story 1 (TDD MANDATORY) ⚠️

- [X] T007 [P] [US1] Write failing contract tests for Product API in `tests/products/test_api.py`
- [X] T008 [P] [US1] Write failing unit tests for Product repository in `tests/products/test_repo.py`

### Implementation for User Story 1

- [X] T009 [P] [US1] Create Product Pydantic DTO in `src/products/dtos/product.py`
- [X] T010 [P] [US1] Create Product lean model in `src/products/models/product.py`
- [X] T011 [P] [US1] Create Product repository in `src/products/repositories/product.py`
- [X] T012 [US1] Register Product repository in `src/project/services.py`
- [X] T013 [US1] Implement Product service in `src/products/services/product.py`
- [X] T014 [US1] Implement Product API endpoints in `src/products/views/product.py`
- [X] T015 [US1] Add basic validation and error handling for product operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Order Placement (Priority: P2)

**Goal**: Place an order for products so that they can be purchased.

**Independent Test**: Create an order linked to existing products and verify the total calculation matches the sum of product prices and quantities.

### Tests for User Story 2 (TDD MANDATORY) ⚠️

- [X] T016 [P] [US2] Write failing contract tests for Order API in `tests/orders/test_api.py`
- [X] T017 [P] [US2] Write failing unit tests for Order repository in `tests/orders/test_repo.py`

### Implementation for User Story 2

- [X] T018 [P] [US2] Create Order and OrderItem Pydantic DTOs in `src/orders/dtos/order.py`
- [X] T019 [P] [US2] Create Order and OrderItem lean models in `src/orders/models/order.py`
- [X] T020 [P] [US2] Create Order repository in `src/orders/repositories/order.py`
- [X] T021 [US2] Register Order repository in `src/project/services.py`
- [X] T022 [US2] Implement Order service with total calculation in `src/orders/services/order.py`
- [X] T023 [US2] Implement Order API endpoints in `src/orders/views/order.py`
- [X] T024 [US2] Integrate with Product repository for stock validation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T025 [P] Finalize project documentation in `docs/`
- [X] T026 [P] Verify SC-001: Benchmark repository creation/retrieval (target < 100ms)
- [X] T027 [P] Run code formatting, linting, and import organization check using `ruff`
- [X] T028 Run final validation of `quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 2 depends on the existence of products (User Story 1) for integration
- **Polish (Final Phase)**: Depends on all user stories being complete

### Parallel Opportunities

- T002, T007, T008, T009, T010, T011, T016, T017, T018, T019, T020 can all run in parallel as they involve different files and apps.
- Setup tasks marked [P] can run in parallel.
- Once Foundational phase completes, US1 and US2 can be worked on in parallel up to the integration point (T024).

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Tests FIRST → Implementation)
4. **STOP and VALIDATE**: Verify product creation and retrieval works via API.

### Incremental Delivery

1. Foundation ready.
2. Add User Story 1 → MVP complete.
3. Add User Story 2 → Full feature complete.
