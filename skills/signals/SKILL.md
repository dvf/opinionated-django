---
name: signals
description: Add reliable signals (async side-effects via Celery) to a Django feature. Use when a business operation needs to trigger post-commit work like notifications, cache invalidation, analytics, or cross-service coordination — any time the user mentions side-effects, events, or async processing tied to a business action.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Add a Reliable Signal

You are adding a reliable signal to an opinionated Django project. Standard Django signals are synchronous and unreliable — receiver failures propagate to the sender, there's no delivery guarantee if the process crashes after commit, and there's no retry. This project uses the reliable signals pattern with Celery instead.

> The pattern implemented here is adapted from Haki Benita's article [Reliable Signals in Django](https://hakibenita.com/django-reliable-signals). Credit for the original design goes to him — read the full article for the rationale and edge cases.

## How It Works

Signal receiver tasks are enqueued **inside the same database transaction** as the business operation. If the transaction rolls back, the tasks roll back too. If it commits, the tasks are guaranteed to be in the queue. Celery processes them asynchronously with at-least-once delivery.

## BEFORE WRITING CODE

1. Read `ARCHITECTURE.md` if present for the full reliable signals reference
2. Find existing signals with `Grep` for `ReliableSignal` under `src/`
3. Find existing receivers with `Glob` for `src/**/receivers.py`
4. Identify which service method should emit the signal and what data needs to travel with it

---

## Step 1: Define the Signal

File: `src/<app>/signals.py`

```python
from project.signals import ReliableSignal

my_event = ReliableSignal()
```

## Step 2: Send from the Service Layer

Call `send_reliable()` **inside** a `transaction.atomic()` block. Arguments MUST be JSON-serializable — pass entity IDs, never model instances:

```python
from django.db import transaction

def create_entity(self, name: str) -> MyEntityDTO:
    with transaction.atomic():
        entity = self.repo.create(name=name)
        my_event.send_reliable(sender=None, entity_id=entity.id)
    return entity
```

## Step 3: Write the Receiver

File: `src/<app>/receivers.py`

```python
from django.dispatch import receiver
from .signals import my_event

@receiver(my_event)
def on_my_event(obj_id: str, **kwargs):
    # Idempotent: guard against duplicate execution
    if already_processed(obj_id):
        return
    do_work(obj_id)
```

**CRITICAL: Every receiver MUST be idempotent.** The system guarantees at-least-once delivery, not exactly-once. A receiver may run more than once for the same event. Design accordingly:

- Check if the action was already performed before performing it
- Use database constraints or flags to prevent duplicate effects
- Never assume a receiver runs exactly once

## Step 4: Load Receivers in `apps.py`

```python
class MyAppConfig(AppConfig):
    def ready(self):
        from . import receivers  # noqa: F401
```

## Step 5: Test

Test receivers in isolation. Mock external dependencies. Verify idempotency by calling the receiver twice with the same arguments:

```python
def test_receiver_is_idempotent():
    on_my_event(obj_id="xxx_fake")
    on_my_event(obj_id="xxx_fake")  # second call must be safe
    # assert side-effect happened exactly once
```

---

## Rules

- NEVER use standard Django `send()` for post-commit side-effects — use `send_reliable()`
- Arguments MUST be JSON-serializable (strings, numbers, booleans) — never model instances
- Receivers MUST be idempotent — this is non-negotiable
- Receivers MUST NOT import or touch ORM models directly — use a repository if DB access is needed
- Receivers MUST NOT call other services that emit signals (no cascading) without careful consideration of idempotency across the chain

---

## VERIFY

```bash
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest
```

If anything fails, fix it and re-run.
