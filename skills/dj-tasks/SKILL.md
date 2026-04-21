---
name: dj-tasks
description: Structure Celery tasks as thin wrappers that delegate to registered services — never the home of business logic. Covers task naming, retry policy defaults, id-only arguments, queue configuration, and how tasks integrate with the svcs service locator. Complements dj-signals (which covers the reliable-signal pattern); this skill covers all Celery tasks, including scheduled ones, admin-triggered ones, and user-triggered ones.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Celery Tasks: Thin Wrappers Over Services

Every Celery task in this project is a **transport adapter**, not a home for business logic. Tasks:

1. Accept JSON-serializable arguments (IDs, primitives — never model instances)
2. Delegate to one registered service method via `get(Service).method(...)`
3. Handle retry via Celery's standard mechanisms

Business logic — validation, orchestration, cross-repo coordination — lives in services per `dj-architecture`. This keeps the same work runnable identically from a view, CLI, admin action, another task, or a unit test: call the service.

## BEFORE WRITING CODE

Read:

- `src/project/services.py` — registered services available via `get(Service)`
- `src/project/settings.py` — Celery config (broker URL, result backend, queue routing)
- Existing `<app>/tasks.py` — naming and retry conventions already in use
- The service you're fronting — if it's not registered, register it first

---

## File Layout

`tasks.py` is flat at first, same as other registry files. When it exceeds the 400-line hard limit or covers more than one concern, convert to `tasks/` per the `dj-architecture` Module Size rule.

```
<app>/
  tasks.py              # small apps: all tasks in one file
  # OR
  tasks/                # larger apps: split by domain concern
    __init__.py         # re-exports public tasks
    billing.py
    notifications.py
    ingestion.py
```

External imports don't change: `from myapp.tasks import charge_customer` works identically either way.

---

## Task Structure

```python
from celery import shared_task

from orders.services.order import OrderService
from project.services import get


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def fulfill_order(self, order_id: str) -> None:
    """Fulfill an order — trigger shipment, invoice, and notification."""
    get(OrderService).fulfill(order_id)
```

**Rules:**

1. **`@shared_task`, not `@app.task`.** `shared_task` is app-agnostic; it resolves the current Celery app lazily so the task works regardless of which Celery instance is active (test vs prod vs inside management commands).
2. **`bind=True`** — gives the task access to `self` for `self.retry()` and `self.request.id`. Mandatory.
3. **Task name matches the verb being performed** in snake_case: `fulfill_order`, `send_welcome_email`, `recalculate_balances`. Never `do_order_stuff`.
4. **Arguments are primitives.** `str` IDs, `int` counts, `bool` flags, simple `dict` payloads. NEVER model instances — they don't round-trip through the broker cleanly and you'll see stale reads after retries.
5. **The function body is ONE line** — delegation to a registered service. If you need a second line, the logic belongs in the service.
6. **Return type is `None` by default.** If you do return a value, it must be JSON-serializable (don't return DTOs with `Decimal` or `datetime` unless the result backend is configured for it).
7. **Docstring states the effect.** One line — `"Fulfill an order — trigger shipment, invoice, and notification."` — not a description of the implementation.

---

## Retry Policy

The skill prescribes a default retry policy that works for most tasks. Override per-task when the work genuinely needs different semantics.

**Default:**

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
```

This gives:
- **Auto-retry on any exception** — `autoretry_for=(Exception,)`
- **3 retries** then permanent failure — `max_retries=3`
- **Exponential backoff** starting at 60s, capped at 600s — `retry_backoff=True`, `retry_backoff_max=600`
- **Jitter** to avoid thundering-herd on correlated failures — `retry_jitter=True`

**When to override:**

- **Idempotent external API calls** → `max_retries=5` is fine; they're safe to retry.
- **Non-idempotent work** (charging a card, sending an SMS) → handle idempotency in the service (by key), then use the default retry — not `max_retries=0`.
- **Fast-failing bad input** (a `ValueError` that means "this will never work") → use `autoretry_for=()` and raise; or filter the exception class: `autoretry_for=(IOError, ConnectionError)` — only retry on transient failures.
- **Long-running jobs** → `default_retry_delay=300` and lower `max_retries` — don't spend an hour retrying a 5-minute task.

**What NOT to do:**

- **Never `try/except` inside the task body** to swallow errors — that silently loses work. Let the exception propagate; Celery + `autoretry_for` handles retries.
- **Never call `self.retry()` manually** unless you need retry semantics the decorator can't express. The decorator path is clearer.

---

## Triggering Tasks

```python
# From a view, service, admin action, CLI command, another task:
fulfill_order.delay(order_id="ord_01jq...")

# With a countdown:
fulfill_order.apply_async(args=["ord_01jq..."], countdown=60)

# Inside a chain:
from celery import chain

chain(
    fulfill_order.s(order_id="ord_01jq..."),
    send_fulfillment_email.s(order_id="ord_01jq..."),
).apply_async()
```

**Rules:**

1. **Chains and groups are built at the CALL SITE** — inside the service method that needs the composition. Never inside a task body (the task is too thin for that). Never inside a view or admin action (that layer is also too thin).
2. **Prefer `.delay(...)` for simple enqueues.** `apply_async(...)` only when you need `countdown`, `eta`, `queue`, or other per-call options.
3. **Pass kwargs, not positional args.** `fulfill_order.delay(order_id="ord_01jq...")`, not `fulfill_order.delay("ord_01jq...")`. Kwargs survive signature changes.

---

## Integration with Reliable Signals

`dj-signals` prescribes reliable signals for transactional side-effects — the receiver runs as a Celery task after `transaction.on_commit`. Those tasks follow the same rules as regular tasks:

- Thin wrapper over a service method
- IDs only, no model instances
- Default retry policy (or project-specified override)
- Must be idempotent (reliable signals are at-least-once)

The difference from regular tasks: reliable-signal receivers are called via `send_reliable(...)`, not `.delay(...)`. Routing is handled inside `dj-signals` machinery.

---

## Periodic Tasks

For scheduled/cron-style tasks, use Celery Beat (or a backend like RedBeat for dynamic scheduling). Register schedules in `src/project/settings.py`:

```python
CELERY_BEAT_SCHEDULE = {
    "recalculate_balances_daily": {
        "task": "accounting.tasks.recalculate_balances",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

The task itself follows the same rules — thin wrapper over a service:

```python
@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3)
def recalculate_balances(self) -> None:
    """Recalculate all account balances nightly."""
    get(AccountingService).recalculate_all()
```

---

## Queue Configuration

Default is a single queue (`celery`). Split queues only when you have a real reason:

- **Isolate long-running tasks** — prevents a 10-minute task from blocking the 5-second queue.
- **Prioritize time-sensitive work** — user-triggered tasks vs background maintenance.

When splitting, configure routing in settings and name the task's queue explicitly:

```python
@shared_task(bind=True, queue="long_running")
def generate_report(self, report_id: str) -> None:
    get(ReportService).generate(report_id)
```

Don't split queues speculatively — every extra queue is an extra worker to deploy and monitor.

---

## Verify

```bash
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest tests/<app>/test_tasks.py
```

- Task tests run with `CELERY_TASK_ALWAYS_EAGER = True` per `dj-pytest`.
- Test the task AND the underlying service separately — task tests prove the wiring (correct service called, correct args passed); service tests prove the logic.
- For reliable-signal receivers: every receiver needs a "called twice, ran once" idempotency test.

---

## Checklist

- [ ] Task uses `@shared_task(bind=True, ...)` with the default retry policy (unless there's a specific reason to override)
- [ ] All arguments are primitives (`str` IDs, `int`, `bool`, simple `dict`) — never model instances
- [ ] Task body is a single line of delegation: `get(Service).method(...)`
- [ ] Task registered in the correct app's `tasks.py` (or `tasks/` subpackage)
- [ ] Task name is a clear snake_case verb
- [ ] Docstring states the effect in one line
- [ ] Triggered via `.delay(kwargs)` or `.apply_async(...)` — never called directly for background work
- [ ] No try/except inside the task body — exceptions bubble to Celery for retry
- [ ] Chains/groups built inside services, not tasks or views
- [ ] If reliable-signal receiver: idempotency test present (see `dj-pytest`)
- [ ] Tests: service logic tested without Celery; task test proves wiring with `CELERY_TASK_ALWAYS_EAGER`
