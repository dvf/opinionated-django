---
name: dj-models
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
- `src/<app>/admin/` — existing admin registrations

---

## File Layout: `models/` and `admin/` Are Directories

Every app's `models` and `admin` MUST be directories, never a flat `models.py` or `admin.py`.

```
<app>/
  models/
    __init__.py      # re-exports every model + __all__
    order.py         # one model per file
    product.py
    customer.py
  admin/
    __init__.py      # imports every admin module to trigger @admin.register
    order.py         # same filename as the model it registers
    product.py
    customer.py
```

**Rules:**

1. **One model per file.** Filenames match the model in snake_case (`order.py` → `Order`, `order_item.py` → `OrderItem`).
2. **`admin/` filenames mirror `models/`.** `models/order.py` registers via `admin/order.py`. Navigation is trivial.
3. **No `_admin` suffix on filenames.** `admin/order.py` — not `admin/order_admin.py`.
4. **`models/__init__.py` re-exports every model** with `__all__`, using relative imports:
   ```python
   from .order import Order, OrderItem
   from .product import Product
   from .customer import Customer

   __all__ = ["Customer", "Order", "OrderItem", "Product"]
   ```
5. **`admin/__init__.py` imports every admin module.** Registration happens via `@admin.register` in each file, but Django only discovers it if the module is imported:
   ```python
   from . import customer  # noqa: F401
   from . import order     # noqa: F401
   from . import product   # noqa: F401
   ```
6. **External imports always go through the package.** `from myapp.models import Order`, never `from myapp.models.order import Order`.
7. **No flat `models.py` migration fallback.** Apps with one model still use a directory. The 10-second upfront cost beats the retrofit cost later.

### Model family exception (narrow)

Two or more models MAY share a single file ONLY when either:

- One is abstract/base and the others are its concrete subtypes (e.g., `Payment` + `CardPayment` + `WirePayment`), AND the subtypes have no meaning or usage outside the base; OR
- One is a "through" model for an M2M that exists solely within that relationship (e.g., `Membership` joining `User` and `Group`), AND the through model is never referenced independently.

"They feel related", "they share a prefix", or "they have a FK between them" are NOT valid reasons. Use Django's string-based FK refs (`models.ForeignKey("app.Model", ...)`) to break circular imports — never combine files to avoid the import.

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
            models.Index(fields=["-created_at"], name="idx_%(class)s_recent"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uq_%(class)s_slug"),
        ]

    # 2. ClassVar prefix
    __prefix__: ClassVar[str] = "xxx"

    # 3. Identifiers — primary key, slugs, external refs
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_xxx_id, editable=False
    )
    slug = models.SlugField(max_length=255)

    # 4. Time fields — created, updated, any dates/datetimes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 5. Workflow / status / state (if applicable)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # 6. Everything else — domain fields
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # 7. Relations — ForeignKey, OneToOne, ManyToMany (always last among fields)
    category = models.ForeignKey("categories.Category", on_delete=models.CASCADE)

    # 8. __str__ — only if useful, and the only method allowed
    def __str__(self) -> str:
        return self.name
```

---

## Rules

### Meta First

`class Meta` is **always** the first thing inside the model body — before `__prefix__`, before the primary key, before any field. This is non-negotiable. It puts the most important structural information (naming, indexes, ordering, constraints) at the top where it's immediately visible.

The ordering inside `Meta` itself:

1. `verbose_name` and `verbose_name_plural`
2. `indexes`
3. `constraints` (unique constraints, check constraints)
4. Anything else (`ordering`, `abstract`, etc.)

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

### Field Ordering

Fields are grouped by role, in this order:

1. **Identifiers** — primary key, slugs, external reference codes, SKUs
2. **Time fields** — `created_at`, `updated_at`, `published_at`, any date or datetime
3. **Workflow / status / state** — `status`, `stage`, `is_active`, `is_published` (skip if the model has no lifecycle)
4. **Domain fields** — everything else: `name`, `description`, `price`, `quantity`, etc.
5. **Relations** — `ForeignKey`, `OneToOneField`, `ManyToManyField` — always last among fields

This ordering makes scanning a model top-to-bottom predictable: "what is it, when was it, where is it in its lifecycle, what does it contain, what does it relate to."

### Uniqueness and Constraints in Meta

All uniqueness and constraints are declared in `Meta.constraints` — never use `unique=True` on individual fields. This keeps all structural rules in one place, right at the top of the model.

```python
class Meta:
    verbose_name = "product"
    verbose_name_plural = "products"
    indexes = [
        models.Index(fields=["-created_at"], name="idx_%(class)s_recent"),
    ]
    constraints = [
        models.UniqueConstraint(fields=["sku"], name="uq_%(class)s_sku"),
        models.UniqueConstraint(fields=["store", "slug"], name="uq_%(class)s_store_slug"),
        models.CheckConstraint(check=models.Q(price__gte=0), name="ck_%(class)s_price_pos"),
    ]
```

Constraint naming convention:
- **Unique:** `uq_%(class)s_<short_description>`
- **Check:** `ck_%(class)s_<short_description>`

`UniqueConstraint` is strictly more powerful than `unique=True` — it supports multi-column uniqueness, conditional uniqueness (`condition=`), and naming. Use it exclusively.

### Field `verbose_name` and `help_text`

Any field whose name is more than one word (joined by underscores) should have an explicit `verbose_name` so it reads cleanly in the admin:

```python
price_at_purchase = models.DecimalField(
    verbose_name="price at purchase",
    max_digits=10,
    decimal_places=2,
)
```

Any field whose purpose is not immediately obvious from its name needs `help_text`. This shows up in the admin form below the field and serves as inline documentation:

```python
idempotency_key = models.CharField(
    max_length=255,
    help_text="Client-generated key to prevent duplicate order submissions.",
)
retention_days = models.IntegerField(
    verbose_name="retention days",
    default=90,
    help_text="Number of days to retain this record before archival.",
)
```

Rules:
- Single-word fields (`name`, `price`, `status`) don't need a `verbose_name` — Django infers it fine
- Multi-word fields (`price_at_purchase`, `is_published`, `created_by`) always get an explicit `verbose_name`
- Obscure or domain-specific fields always get `help_text` — if a new developer would need to ask "what is this?", add it
- Keep `help_text` to one sentence, written for someone reading the admin form

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
- **Don't duplicate** — Django auto-creates an index for every `ForeignKey` and `UniqueConstraint`. Don't add a redundant single-column index for those.
- **Don't over-index** — every index slows writes. Three or four well-chosen indexes beat eight speculative ones.

### No Business Logic

Models contain ZERO business logic:

- No custom managers
- No `save()` overrides
- No signals
- No properties that compute
- `__str__` is the only method allowed — and only if it adds value (skip it if the default `ModelName object (pk)` is fine)

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
    fieldsets = (
        (None, {"fields": ("id", "date")}),
        ("Details", {"fields": ("total",)}),
    )
    inlines = [OrderItemInline]
```

### Admin Rules

- **`list_display`** — `id` first, then the most useful columns. Keep it to 4-6 fields max for readability.
- **`list_per_page = 25`** — default 100 is too slow on large tables. 25 keeps the admin snappy.
- **`search_fields`** — always include `id`. Add name/title fields if they exist. Never search on unindexed columns.
- **`readonly_fields`** — always include `id` (ULID PKs should never be edited). Add computed or auto-set fields.
- **`ordering`** — explicit ordering so the admin doesn't rely on the default PK sort. Use `-created_at` or the most natural time field.
- **`fieldsets`** — structure the change view for readability. Always place identifiers (`id`, timestamps) in the first fieldset at the top so they're immediately visible. Group remaining fields logically:
  ```python
  fieldsets = (
      (None, {"fields": ("id", "created_at", "updated_at")}),
      ("Details", {"fields": ("name", "description", "status")}),
      ("Relations", {"fields": ("category",)}),
  )
  ```
  The first fieldset (with `None` title) keeps IDs and timestamps prominent with no collapsible header. Use named sections for the rest.
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
            models.Index(fields=["status", "-date"], name="idx_%(class)s_status_recent"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="uq_%(class)s_idempotency",
            ),
        ]

    __prefix__: ClassVar[str] = "ord"

    # Identifiers
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_ord_id, editable=False
    )
    idempotency_key = models.CharField(
        verbose_name="idempotency key",
        max_length=255,
        help_text="Client-generated key to prevent duplicate order submissions.",
    )

    # Time
    date = models.DateTimeField(auto_now_add=True)

    # Status
    status = models.CharField(max_length=20, default="pending")

    # Domain
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

    # Identifiers
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_itm_id, editable=False
    )

    # Domain
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(
        verbose_name="price at purchase",
        max_digits=10,
        decimal_places=2,
        help_text="Snapshot of the product price at the time the order was placed.",
    )

    # Relations
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

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
    list_display = ("id", "status", "date", "total")
    list_per_page = 25
    search_fields = ("id", "idempotency_key")
    readonly_fields = ("id", "date")
    ordering = ("-date",)
    date_hierarchy = "date"
    fieldsets = (
        (None, {"fields": ("id", "date")}),
        ("Details", {"fields": ("status", "total", "idempotency_key")}),
    )
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
- [ ] Field order: identifiers → time → status/state → domain → relations
- [ ] All indexes in `Meta.indexes` — no `db_index=True` on fields
- [ ] All uniqueness in `Meta.constraints` via `UniqueConstraint` — no `unique=True` on fields
- [ ] Check constraints in `Meta.constraints` where applicable
- [ ] Indexes match actual query patterns from the repository layer
- [ ] No over-indexing — only index what is queried
- [ ] Multi-word fields have explicit `verbose_name`
- [ ] Obscure or domain-specific fields have `help_text`
- [ ] No business logic — no custom managers, `save()`, signals, or computed properties
- [ ] `__str__` only if useful, and the only method allowed
- [ ] Model registered in admin with `list_display`, `list_per_page = 25`, `search_fields`, `readonly_fields`, `ordering`, `fieldsets`
- [ ] `fieldsets` places `id` and timestamps in the first (untitled) fieldset at the top of the change view
- [ ] FKs to large tables use `raw_id_fields` or `autocomplete_fields`
- [ ] Inlines use `extra = 0` and `show_change_link = True`
- [ ] Migrations generated and applied
- [ ] ruff, pyrefly, pytest all pass
