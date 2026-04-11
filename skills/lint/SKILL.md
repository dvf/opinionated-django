---
name: lint
description: Run linting, formatting, and static type checks on a Django project using ruff and pyrefly, and fix any issues found. Use after making code changes, before committing, or whenever the user asks to lint, format, or type-check the codebase.
allowed-tools: Bash, Read, Edit
---

# Lint and Type-Check

Run the full static-analysis suite on the project and fix any issues found.

1. `uv run ruff check src` — lint the code
2. `uv run ruff format --check src` — verify formatting
3. `uv run pyrefly check src` — static type analysis

Fix every issue reported (re-run until clean) and report a short summary of what changed when done. If a failure is not auto-fixable, explain what needs human judgement rather than silencing it.
