---
name: models
description: Structure Django models with proper Meta classes, verbose names, and optimized indexes. Use when creating or reviewing Django models to ensure consistent ordering, correct verbose_name/verbose_name_plural, and database indexes aligned to actual query patterns. Also registers every model in the admin with a clean, fast-loading configuration.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Structure a Django Model

You are defining or restructuring a Django model in an opinionated, fully type-safe Django project. Every convention below is mandatory. Do not deviate.

## BEFORE WRITING CODE

Read the model file being created or modified, plus:

- `src/project/ids.py` — existing ID prefixes
- Any existing models in the same app — for cross-model index considerations
- The repository that queries this model — to understand real query patterns
- `src/<app>/admin.py` — existing admin registrations

---

## Model Structure

Every model follows this exact ordering of members:

```python
from typing import ClassVar

from django.db import models

from project.ids import generate_xxx_id


class MyEntity(models.Model):
    # 1. Meta — ALWAYS first, before any field
    class Meta:
        verbose_name = "my entity"
        verbose_name_plural = "my entities"
        indexes = [
            models.Index(fields=["created_at"], name="idx_%(class)s_created"),
        ]

    # 2. ClassVar prefix
    __prefix__: ClassVar[str] = "xxx"

    # 3. Primary key
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_xxx_id, editable=False
    )

    # 4. Foreign keys and relations
    # 5. Required fields
    # 6. Optional fields
    # 7. Timestamp fields (created_at, updated_at — always last among fields)

    # 8. __str__ — the only method allowed
    def __str__(self) -> str:
        return self.name
```

---

## Rules

### Meta First

`class Meta` is **always** the first thing inside the model body — before `__prefix__`, before the primary key, before any field. This is non-negotiable. It puts the most important structural information (naming, indexes, ordering, constraints) at the top where it's immediately visible.

### Always Declare `verbose_name` and `verbose_name_plural`

Every model's `Meta` must include both:

```python
class Meta:
    verbose_name = "order item"
    verbose_name_plural = "order items"
```

- Use lowercase, human-readable English
- Never rely on Django's automatic pluralization — it gets edge cases wrong (`"categorys"`, `"order items"` → `"order itemss"`)
- The `verbose_name` should read naturally in admin headers and log messages

### Specify Indexes in Meta

All indexes are declared in `Meta.indexes` — never use `db_index=True` on individual fields. Centralizing indexes makes them reviewable at a glance and enables composite indexes that `db_index=True` cannot express.

```python
class Meta:
    verbose_name = "order"
    verbose_name_plural = "orders"
    indexes = [
        models.Index(fields=["customer", "created_at"], name="idx_%(class)s_cust_created"),
        models.Index(fields=["status", "-created_at"], name="idx_%(class)s_status_recent"),
    ]
```

Index naming convention: `idx_%(class)s_<short_description>` — Django interpolates `%(class)s` to the lowercased model name, keeping names unique across models.

### Optimize Indexes for How the Model Is Used

Don't index speculatively. Read the repository that queries this model and index for the queries that actually exist:

- **Filter + order** → composite index with filter columns first, order column last: `fields=["status", "-created_at"]`
- **Foreign key lookups** → Django auto-creates indexes on `ForeignKey` fields, but if you always filter the FK *with* another column, replace it with a composite: `fields=["order", "product"]`
- **Prefix for descending sort** → use `-` prefix: `fields=["-created_at"]` for queries that `ORDER BY created_at DESC`
- **Covering queries** → if a query only reads a small set of columns, consider `include` (Postgres): `models.Index(fields=["status"], include=["total"], name="idx_%(class)s_status_cov")`
- **Partial indexes** → if a query always filters on a condition, use `condition`: `models.Index(fields=["created_at"], condition=models.Q(status="pending"), name="idx_%(class)s_pending")`
- **Don't duplicate** — Django auto-creates an index for every `ForeignKey` and `unique=True` field. Don't add a redundant single-column index for those.
- **Don't over-index** — every index slows writes. Three or four well-chosen indexes beat eight speculative ones.

### No Business Logic

Models contain ZERO business logic:

- No custom managers
- No `save()` overrides
- No signals
- No properties that compute
- `__str__` is the only method allowed

---

## Admin Registration

Every model gets registered in `src/<app>/admin.py` with a clean, fast-loading configuration. The admin should be **aesthetic** — well-organized, readable, and snappy even on large tables.

```python
from django.contrib import admin

from .models.order import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("id", "product", "quantity", "price_at_purchase")
    readonly_fields = ("id",)
    extra = 0
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "total")
    list_per_page = 25
    search_fields = ("id",)
    readonly_fields = ("id",)
    ordering = ("-date",)
    inlines = [OrderItemInline]
```

### Admin Rules

- **`list_display`** — `id` first, then the most useful columns. Keep it to 4-6 fields max for readability.
- **`list_per_page = 25`** — default 100 is too slow on large tables. 25 keeps the admin snappy.
- **`search_fields`** — always include `id`. Add name/title fields if they exist. Never search on unindexed columns.
- **`readonly_fields`** — always include `id` (ULID PKs should never be edited). Add computed or auto-set fields.
- **`ordering`** — explicit ordering so the admin doesn't rely on the default PK sort. Use `-created_at` or the most natural time field.
- **`list_select_related`** — specify FK fields shown in `list_display` to avoid N+1 queries: `list_select_related = ("customer",)`
- **`raw_id_fields`** — use for any FK to a large table. The default dropdown loads every row: `raw_id_fields = ("product",)`
- **`extra = 0`** on inlines — never show empty inline forms by default.
- **`show_change_link = True`** on inlines — lets you click through to the inline's own admin page.
- **`TabularInline`** for child models on the parent's admin.
- **No `list_filter` on unindexed columns** — filtering on unindexed columns causes full table scans.
- **`autocomplete_fields`** — prefer over `raw_id_fields` when the related model has `search_fields` configured for a better UX: `autocomplete_fields = ("customer",)`
- **`date_hierarchy`** — use on the primary date field if the model is time-series-like (orders, events, logs). Only use on indexed date fields.

---

## Full Example

```python
from typing import ClassVar

from django.db import models

from products.models.product import Product
from project.ids import generate_itm_id, generate_ord_id


class Order(models.Model):
    class Meta:
        verbose_name = "order"
        verbose_name_plural = "orders"
        indexes = [
            models.Index(fields=["-date"], name="idx_%(class)s_recent"),
        ]

    __prefix__: ClassVar[str] = "ord"

    id = models.CharField(
        max_length=64, primary_key=True, default=generate_ord_id, editable=False
    )
    date = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"Order {self.id} on {self.date}"


class OrderItem(models.Model):
    class Meta:
        verbose_name = "order item"
        verbose_name_plural = "order items"
        indexes = [
            models.Index(fields=["order", "product"], name="idx_%(class)s_ord_prd"),
        ]

    __prefix__: ClassVar[str] = "itm"

    id = models.CharField(
        max_length=64, primary_key=True, default=generate_itm_id, editable=False
    )
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name} (Order {self.order_id})"  # type: ignore[attr-defined]
```

Admin for the example above:

```python
from django.contrib import admin

from .models.order import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("id", "product", "quantity", "price_at_purchase")
    readonly_fields = ("id",)
    extra = 0
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "total")
    list_per_page = 25
    search_fields = ("id",)
    readonly_fields = ("id",)
    ordering = ("-date",)
    date_hierarchy = "date"
    inlines = [OrderItemInline]
```

---

## Verify

After creating or modifying models:

```bash
uv run python src/manage.py makemigrations && uv run python src/manage.py migrate
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest
```

All must pass. Fix any issue rather than silencing it.

## Checklist

- [ ] `class Meta` is the first thing inside the model body
- [ ] `verbose_name` and `verbose_name_plural` are set — never relying on Django's auto-pluralization
- [ ] All indexes are in `Meta.indexes` — no `db_index=True` on fields
- [ ] Indexes match actual query patterns from the repository layer
- [ ] No over-indexing — only index what is queried
- [ ] No business logic — no custom managers, `save()`, signals, or computed properties
- [ ] `__str__` is the only method
- [ ] Model registered in admin with `list_display`, `list_per_page = 25`, `search_fields`, `readonly_fields`, `ordering`
- [ ] FKs to large tables use `raw_id_fields` or `autocomplete_fields`
- [ ] Inlines use `extra = 0` and `show_change_link = True`
- [ ] Migrations generated and applied
- [ ] ruff, pyrefly, pytest all pass
