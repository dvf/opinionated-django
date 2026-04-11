---
name: prefixed-ulids
description: Use Stripe-style prefixed ULID primary keys (e.g. `prd_01jq3v...`) for every Django model instead of integers or UUIDs. Use when setting up a new model, reviewing a schema that still uses auto-increment or UUID primary keys, or when the user mentions IDs, slugs, public identifiers, or referential debugging. Produces short readable prefixes, time-sortable values, and IDs that are safe to expose in URLs and logs.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Prefixed ULID Primary Keys

This project uses **Stripe-style prefixed ULIDs** as the primary key for every Django model:

```
prd_01jq3v8f6a7b2c8d9e0f1g2h3j4k
ord_01jq3v8fgh7x2y5z9a1b2c3d4e5f
```

A 3-4 character prefix identifies the entity type, followed by an underscore and a lowercase [ULID](https://github.com/ulid/spec). ULIDs are 128-bit, lexicographically sortable by creation time, URL-safe, and collision-resistant.

## Why

- **Debuggable.** `ord_01jq...` in a log line tells you immediately it's an order — no need to cross-reference the column.
- **Safe to expose.** Unlike auto-increment integers, prefixed ULIDs leak no ordering or volume information, and unlike opaque UUIDs they remain human-readable.
- **Time-sortable.** ULIDs sort chronologically, so `ORDER BY id` doubles as `ORDER BY created_at` without a second index.
- **Type-safe across layers.** Every ID is a `str` end-to-end — no `UUID` / `str` coercion at the service/API boundary.
- **No integer collisions.** Exporting, importing, and sharding are all easier without monotonic counters.

## The Generator

Put this in `src/project/ids.py`:

```python
from ulid import ULID


def prefixed_ulid(prefix: str) -> str:
    return f"{prefix}_{str(ULID()).lower()}"


def _make_generator(prefix: str):
    def generate() -> str:
        return prefixed_ulid(prefix)

    generate.__name__ = f"generate_{prefix}_id"
    generate.__qualname__ = f"generate_{prefix}_id"
    return generate
```

Then register a generator per aggregate root:

```python
generate_prd_id = _make_generator("prd")
generate_ord_id = _make_generator("ord")
generate_itm_id = _make_generator("itm")
```

The `__name__` / `__qualname__` rewrite matters: Django migrations serialize the default callable's fully qualified name, so each generator needs a distinct identity or the autodetector will get confused.

## Choosing a Prefix

- 3 to 4 lowercase letters — short enough to stay readable in logs
- Must be unique across the whole project
- Prefer mnemonic, not cryptic: `ord` for order, `inv` for invoice, `prd` for product, `usr` for user
- Avoid collisions with existing prefixes — grep `src/project/ids.py` before inventing a new one
- Never rename a prefix once it's in production; the prefix is part of the ID

## Using it in a Model

```python
from typing import ClassVar

from django.db import models

from project.ids import generate_prd_id


class Product(models.Model):
    __prefix__: ClassVar[str] = "prd"
    id = models.CharField(
        max_length=64,
        primary_key=True,
        default=generate_prd_id,
        editable=False,
    )
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name
```

Rules:

- `CharField(max_length=64)` — ULID is 26 chars, prefix + separator adds up to ~10, 64 leaves headroom.
- `primary_key=True` and `editable=False`.
- The `default` is the generator **function** (no parentheses) so Django calls it per row.
- `__prefix__: ClassVar[str]` mirrors the generator's prefix — makes the mapping discoverable from the model class alone, and lets tests assert on it.
- **Never** override `save()` to generate the ID; the default handles it.

## Using it Across the Stack

Once IDs are strings at the ORM layer, they stay strings everywhere else:

- **DTOs** (Pydantic): `id: str` — never `UUID`.
- **Repository params**: `def get(self, product_id: str) -> ProductDTO: ...`
- **API path params** (django-ninja): `def get_product(request, product_id: str): ...`
- **Celery task args**: pass the string ID, never a model instance.
- **Tests**: assert on the prefix, e.g. `assert dto.id.startswith("prd_")`.

The prefix is also a cheap sanity check on every boundary: if an ID ever shows up without its prefix, something has stripped or regenerated it incorrectly.

## Migrating an Existing Table

If the table already has integer or UUID primary keys, don't try to change them in place. Instead:

1. Add a new `CharField` column with the prefixed ULID default, nullable at first.
2. Backfill with a data migration that assigns `prefixed_ulid("prd")` to every existing row.
3. Add `unique=True` and make it non-nullable in a follow-up migration.
4. Swap it to `primary_key=True` only after every foreign key has been migrated to reference the new column — this usually means a multi-release cutover.

Prefer doing this on a new table where possible; in-place primary-key swaps in production are a lot of work for limited benefit.

## Verify

- Every model has `__prefix__` and a `CharField` primary key using a `generate_*_id` default.
- Every `generate_*_id` in `src/project/ids.py` has a unique prefix.
- No model uses `UUIDField`, `AutoField`, or `BigAutoField` for its primary key.
- No DTO field, service argument, or API path param types an ID as `UUID` — they're all `str`.

```bash
uv run ruff check src
uv run pyrefly check src
uv run pytest
```
