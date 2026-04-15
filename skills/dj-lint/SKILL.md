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

## Pyrefly + Django gotchas

Pyrefly has built-in Django support (via `django-stubs`), but a few things aren't covered yet. Recognize these before reaching for `# type: ignore`:

- **Reverse relations (`user.order_set`, `author.article_set`) are not supported.** This is a known pyrefly limitation, not a real bug. The right fix is to query the child model directly from its repository (`OrderRepository().list_for_user(user_id)`) — push the access down into the repo layer rather than suppressing it. Only if that's impossible, narrow it with `# type: ignore[attr-defined]` at a single call site.
- **`ManyRelatedManager` is generic over `[Parent, Model]`**, not the concrete child. Don't rely on pyrefly to catch a mistyped M2M target — cover it with a test instead.
- **Chained QuerySet methods beyond `.all()` are thinly typed.** Keep chains inside the repository where the return type is an annotated `list[SomeDTO]`; don't let querysets leak out into services.

See [pyrefly.org/en/docs/django](https://pyrefly.org/en/docs/django/) for the current support matrix. Pyrefly's Django support is actively evolving — re-check when upgrading.
