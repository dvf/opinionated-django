# Tasks: Django Type Stubs

**Input**: Design documents from `/specs/002-django-type-stubs/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md

**Tests**: Included per constitution (TDD mandate).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add type-checking toolchain to the project

- [x] T001 Add pyright and django-types dev dependencies via `uv add --dev pyright django-types`
- [x] T002 Add `[tool.pyright]` configuration section to pyproject.toml with pythonVersion="3.14", include=["src"], venvPath=".", venv=".venv"

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the ServiceRequest type that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create ServiceRequest class in src/project/types.py that extends HttpRequest with `services: svcs.Container` attribute
- [x] T004 Add type annotations to SvcsMiddleware in src/project/middleware.py (type get_response callable, request parameter)

**Checkpoint**: Foundation ready — ServiceRequest type exists and middleware is annotated

---

## Phase 3: User Story 1 - Type-Safe Access to request.services (Priority: P1) 🎯 MVP

**Goal**: All views and API handlers use `ServiceRequest` and pass type checking with zero errors on `request.services`

**Independent Test**: Run `uv run pyright src/products/api.py src/orders/api.py` — zero errors for `request.services` access

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [US1] Write type-checking validation test in tests/test_types.py that imports ServiceRequest, asserts `services` attribute is typed as `svcs.Container`, and verifies it inherits from HttpRequest

### Implementation for User Story 1

- [x] T006 [P] [US1] Update request type annotation from HttpRequest to ServiceRequest in src/products/api.py
- [x] T007 [P] [US1] Update request type annotation from HttpRequest to ServiceRequest in src/products/views/product.py
- [x] T008 [P] [US1] Update request type annotation from HttpRequest to ServiceRequest in src/orders/api.py
- [x] T009 [P] [US1] Update request type annotation from HttpRequest to ServiceRequest in src/orders/views/order.py
- [x] T010 [US1] Run `uv run pyright src/` and verify zero type errors for all `request.services` access across the project

**Checkpoint**: All views/APIs use ServiceRequest, pyright reports zero errors on `request.services`

---

## Phase 4: User Story 2 - Zero-Config Stub Discovery (Priority: P2)

**Goal**: Type checking works automatically after `uv sync` — no manual configuration needed beyond what's in the repo

**Independent Test**: Verify pyright discovers ServiceRequest and all dependencies (svcs, django-types) without additional setup beyond `uv sync`

### Tests for User Story 2

- [x] T011 [US2] Write test in tests/test_types.py that verifies ServiceRequest can be imported from project.types and that svcs.Container is resolvable (confirms dependency chain works)

### Implementation for User Story 2

- [x] T012 [US2] Verify `uv sync && uv run pyright src/` succeeds with zero configuration beyond pyproject.toml (fix any discovery issues in [tool.pyright] config)
- [x] T013 [US2] Add `__all__` export for ServiceRequest in src/project/types.py to make the public API explicit

**Checkpoint**: Fresh `uv sync` + `uv run pyright` works with no extra steps

---

## Phase 5: User Story 3 - Stubs Stay In Sync with Runtime Code (Priority: P2)

**Goal**: If middleware changes the type assigned to `request.services`, the type checker catches the mismatch

**Independent Test**: Temporarily change middleware to assign a non-Container type, run pyright, confirm it reports an error

### Tests for User Story 3

- [x] T014 [US3] Write test in tests/test_types.py that programmatically verifies the middleware assigns an `svcs.Container` instance to `request.services` (runtime check that mirrors the static type declaration)

### Implementation for User Story 3

- [x] T015 [US3] Add a pyright check command to pyproject.toml scripts section (e.g., `[tool.scripts]` or document the `uv run pyright` command in README.md) so developers have a standard way to run type checks
- [x] T016 [US3] Run full type-check pass with `uv run pyright src/` and fix any remaining type errors across the entire codebase

**Checkpoint**: Type checker catches stub/runtime mismatches; developers have a documented check command

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T017 Run `ruff check src/project/types.py` and `ruff format src/project/types.py` to ensure new file passes linting
- [x] T018 Run full test suite with `uv run pytest` to confirm no regressions from type annotation changes
- [x] T019 Run quickstart.md validation: execute the verification steps from specs/002-django-type-stubs/quickstart.md end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 (Phase 3) can proceed independently after Phase 2
  - US2 (Phase 4) can proceed independently after Phase 2
  - US3 (Phase 5) can proceed independently after Phase 2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — independent of US1
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — independent of US1/US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks marked [P] can run in parallel
- Final validation task runs after all implementation tasks

### Parallel Opportunities

- T006, T007, T008, T009 can all run in parallel (different files)
- All user stories (Phase 3, 4, 5) can run in parallel after Phase 2
- T017, T018 can run in parallel

---

## Parallel Example: User Story 1

```bash
# After T005 test is written and failing, launch all view updates in parallel:
Task T006: "Update request type in src/products/api.py"
Task T007: "Update request type in src/products/views/product.py"
Task T008: "Update request type in src/orders/api.py"
Task T009: "Update request type in src/orders/views/order.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T010)
4. **STOP and VALIDATE**: Run `uv run pyright src/` — zero errors on `request.services`
5. This alone delivers the core value of the feature

### Incremental Delivery

1. Setup + Foundational → Toolchain ready
2. User Story 1 → Type-safe `request.services` access (MVP!)
3. User Story 2 → Zero-config discovery validated
4. User Story 3 → Sync enforcement in place
5. Polish → Full validation pass

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Constitution mandates TDD — tests are written before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
