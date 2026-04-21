---
name: dj-lint
description: Run linting, formatting, and static type checks on a Django project using ruff and pyrefly, and fix any issues found. Use after making code changes, before committing, or whenever the user asks to lint, format, or type-check the codebase.
allowed-tools: Bash, Read, Edit
---

# Lint and Type-Check

Run the full static-analysis suite on the project and fix any issues found.

1. `uv run ruff check src` — lint the code
2. `uv run ruff format --check src` — verify formatting
3. `uv run pyrefly check src` — static type analysis

Fix every issue reported (re-run until clean) and report a short summary of what changed when done. If a failure is not auto-fixable, explain what needs human judgement rather than silencing it.

## Import Rules

### Absolute imports everywhere except `__init__.py`

All imports MUST be absolute. Relative imports (`from .foo import Foo`) are allowed ONLY in `__init__.py` files that re-export siblings. Elsewhere, use the full dotted path (`from products.models import Product`).

**Why:** absolute imports survive file moves, make dependencies greppable at a glance, and match PEP 8's recommendation. Relative imports in `__init__.py` is the only case where relative is idiomatic — the package is gathering its public surface, and absolute imports there would just be noise.

Enforced by ruff's `flake8-tidy-imports` (TID252):

```toml
[tool.ruff.lint]
select = [..., "TID"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.lint.per-file-ignores]
"**/__init__.py" = ["TID252"]
```

### Inline imports are exceptional

Module-level imports are the default. Imports inside function or method bodies are allowed ONLY for:

1. **`apps.py` `ready()` signal registration** — `from . import receivers` is idiomatic Django
2. **Breaking true circular imports** — prefer Django string FKs (`"app.Model"`) first; inline import is a last resort
3. **Test fixtures / conftest** — scope-controlled imports inside fixture functions
4. **Expensive imports deferred to first call** — rare case (e.g., loading a large ML model, connecting to an optional SaaS SDK). Document the reason in a one-line comment

Inline imports are NOT allowed to hide architectural cycles in business logic, "clean up" module-top imports, or defer ordinary Django/stdlib imports.

Enforced by ruff's `pylint` rule `PLC0415` (import-outside-toplevel) with per-file-ignores for the idiomatic cases:

```toml
[tool.ruff.lint]
select = [..., "PLC0415"]

[tool.ruff.lint.per-file-ignores]
"**/apps.py" = ["PLC0415"]
"**/tests/**" = ["PLC0415"]
"**/conftest.py" = ["PLC0415"]
```

## Pyrefly + Django gotchas

Pyrefly has built-in Django support (via `django-stubs`), but a few things aren't covered yet. Recognize these before reaching for `# type: ignore`:

- **Reverse relations (`user.order_set`, `author.article_set`) are not supported.** This is a known pyrefly limitation, not a real bug. The right fix is to query the child model directly from its repository (`OrderRepository().list_for_user(user_id)`) — push the access down into the repo layer rather than suppressing it. Only if that's impossible, narrow it with `# type: ignore[attr-defined]` at a single call site.
- **`ManyRelatedManager` is generic over `[Parent, Model]`**, not the concrete child. Don't rely on pyrefly to catch a mistyped M2M target — cover it with a test instead.
- **Chained QuerySet methods beyond `.all()` are thinly typed.** Keep chains inside the repository where the return type is an annotated `list[SomeDTO]`; don't let querysets leak out into services.

See [pyrefly.org/en/docs/django](https://pyrefly.org/en/docs/django/) for the current support matrix. Pyrefly's Django support is actively evolving — re-check when upgrading.
