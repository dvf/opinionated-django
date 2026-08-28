---
name: dj-user
description: Custom User model based on AbstractBaseUser + PermissionsMixin with a complete UserManager (get_by_natural_key / _create_user / create_user / create_superuser) and a project-wide RoleEnum. Use when scaffolding the first User model in a new Django project, or when an existing project wants email-as-username + role-based auth without inheriting Django's groups/permissions baseline via AbstractUser. Pairs with dj-prefixed-ulids for the User PK and with dj-settings for the AUTH_USER_MODEL wiring.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Custom User Model with `AbstractBaseUser`

You are scaffolding the User model for an opinionated, type-safe Django project. Every convention below is mandatory. Do not deviate.

This skill exists because every project that uses `AbstractBaseUser` (instead of `AbstractUser`) walks into the same trap: `manage.py createsuperuser` calls `User.objects.create_superuser(...)` unconditionally, and `AbstractBaseUser` does not provide it. The complete `UserManager` quartet below is the canonical fix.

## BEFORE WRITING CODE

Read first:

- `src/project/ids.py` — confirm no `usr` prefix is already registered.
- `src/project/settings.py` — confirm `AUTH_USER_MODEL` is not yet set.
- Any existing `accounts/` app — confirm this is a fresh scaffold and not an in-place swap.

**Critical precondition.** This skill must be applied BEFORE the project's first `migrate`. Swapping `AUTH_USER_MODEL` on a project that already has migrations is a multi-release cutover, not a skill-driven scaffold. Django bakes the user-model reference into the migration graph; changing it after the fact requires deleting and regenerating every migration that references auth (which is most of them, since `django.contrib.auth` ships with migrations).

If `python src/manage.py showmigrations` lists ANY applied migrations on a non-fresh database, STOP and resolve the cutover plan first.

## Why a Custom Manager — and Why This Model Is the Only Exception

The `dj-models` skill states "no custom managers." This skill is the **single project-wide exception**, because Django's auth surface requires it:

- `manage.py createsuperuser` calls `User.objects.create_superuser(...)`.
- The default `auth` backend calls `User.objects.get_by_natural_key(...)` during login.

Neither method exists on `BaseUserManager`. They must be defined on a custom manager that the `User` model binds via `objects = UserManager()`. Skipping this is not an option; trying to route creation through a service layer alone breaks `createsuperuser` at the moment of invocation.

No other model in the project ships a custom manager. The User model is uniquely entangled with Django's framework-level auth contract.

## Step 1 — Register the ULID generator

In `src/project/ids.py` (per `dj-prefixed-ulids`), add:

```python
generate_usr_id = _make_generator("usr")
```

`usr` is the convention. Grep `src/project/ids.py` first to confirm the prefix is not already taken by another aggregate root.

## Step 2 — Create the accounts app

```bash
uv run python src/manage.py startapp accounts src/accounts
```

The default app name is `accounts`. Use a different name only if the project has a strong convention (e.g. `users`, `identity`); the rest of this skill assumes `accounts`.

Register the app in `src/project/settings.py` under `INSTALLED_APPS` (per `dj-settings`' APPLICATION DEFINITION section), in the project-apps sub-group:

```python
INSTALLED_APPS = [
    # Django core
    ...
    # Third-party
    ...
    # Project apps
    "accounts.apps.AccountsConfig",
]
```

## Step 3 — Define the role enum

`src/accounts/enums.py`:

```python
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
```

Rules:

- Use `TextChoices`, not raw tuples or `IntegerChoices`.
- Values are lowercase + underscore-separated. Labels are title-case for admin display.
- The three defaults (`SUPER_ADMIN`, `ADMIN`, `MEMBER`) cover most projects. Add new members one per line; never rename or reorder existing members in production (the string values become part of stored data and any rename is a data migration).
- The role enum is project-local — it is a `dj-user` convention, not a Django concept. Custom permission machinery (django-rules, django-guardian, custom predicates) reads from `user.role` rather than from Django's `groups` / `user_permissions`.

## Step 4 — Define the User model

`src/accounts/models.py`:

```python
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from accounts.enums import Role
from accounts.managers import UserManager
from project.ids import generate_usr_id


class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uq_%(class)s_email"),
        ]

    __prefix__: ClassVar[str] = "usr"

    # Identifiers
    id = models.CharField(
        max_length=64, primary_key=True, default=generate_usr_id, editable=False
    )
    email = models.EmailField()

    # Time
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Domain
    role = models.CharField(
        max_length=32, choices=Role.choices, default=Role.MEMBER
    )

    objects: ClassVar[UserManager] = UserManager()  # type: ignore[misc]

    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    def __str__(self) -> str:
        return self.email
```

Rules (per `dj-models` field ordering and `Meta`-first conventions):

- `class Meta` is the first member, before `__prefix__` and any field.
- Uniqueness on `email` goes in `Meta.constraints` via `UniqueConstraint`, not as `unique=True` on the field.
- `AbstractBaseUser` provides `password`, `last_login`, `get_session_auth_hash()`. It does NOT provide `is_active`, `is_staff`, `is_superuser`, `groups`, `user_permissions`.
- `PermissionsMixin` provides `is_superuser`, `groups`, `user_permissions`, `has_perm()`, `has_module_perms()`. The mixin is required for Django admin to function correctly.
- `is_active` and `is_staff` are explicit `BooleanField` declarations — neither base class supplies them.
- `USERNAME_FIELD = "email"` makes email the natural key. The `email` field is automatically required at the `createsuperuser` prompt; do NOT add it to `REQUIRED_FIELDS` (Django excludes the USERNAME_FIELD from that list by definition).
- `REQUIRED_FIELDS = []` — only `email` is required at `createsuperuser` time. If the project later requires (say) a display name at superuser creation, add the field to the model AND to `REQUIRED_FIELDS`.
- `objects = UserManager()` binds the custom manager (next step). The `type: ignore[misc]` silences a known Django typing quirk where the generic `BaseUserManager["User"]` parameterization confuses some type checkers at the binding line.

## Step 5 — Define the UserManager

`src/accounts/managers.py`:

```python
from typing import TYPE_CHECKING, Any

from django.contrib.auth.models import BaseUserManager

from accounts.enums import Role

if TYPE_CHECKING:
    from accounts.models import User


class UserManager(BaseUserManager["User"]):
    def get_by_natural_key(self, email: str) -> "User":
        return self.get(email=email)

    def _create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        if not email:
            raise ValueError("email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", Role.MEMBER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.SUPER_ADMIN)
        if extra_fields["is_staff"] is not True:
            raise ValueError("superuser must have is_staff=True")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)
```

Rules:

- All four methods are mandatory. Do not omit any.
- `_create_user` is the private workhorse. Both public creators delegate to it — single source of truth for `normalize_email`, `set_password`, and the `save(using=self._db)` write. Multi-database setups depend on `using=self._db`.
- `create_user` defaults to a non-privileged user (`is_staff=False`, `is_superuser=False`, `role=Role.MEMBER`). `extra_fields.setdefault(...)` lets callers override per-call.
- `create_superuser` defaults to the privileged shape AND validates that the caller did not silently downgrade via `extra_fields`. If a caller passes `is_staff=False` to `create_superuser`, refuse loudly — that is almost always a bug.
- The `TYPE_CHECKING` import block lets `UserManager` reference `"User"` for return types without a runtime circular import (`models.py` imports `UserManager`; `UserManager` would otherwise import `User`).
- The generic parameter `BaseUserManager["User"]` gives type-safe `self.model` and `self.get(...)` calls. Some type checkers struggle with this at the `objects = UserManager()` binding line in `models.py`; the `type: ignore[misc]` there is the documented workaround.

## Step 6 — Wire `AUTH_USER_MODEL`

In `src/project/settings.py`, under the `AUTH` section (per `dj-settings`' section order):

```python
# =============================================================================
# AUTH
# =============================================================================
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

`AUTH_USER_MODEL` MUST be set before the first `migrate`. See the precondition note at the top of this skill.

## Step 7 — Generate the initial migration

```bash
uv run python src/manage.py makemigrations accounts
uv run python src/manage.py migrate
```

Verify the generated migration creates one `accounts.User` table with a `CharField` primary key, an `EmailField`, the role + status fields, and the m2m through tables for `groups` and `user_permissions` (provided by `PermissionsMixin`).

## Step 8 — Register in admin

`src/accounts/admin.py`:

```python
from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "role", "is_active", "is_staff", "is_superuser")
    list_per_page = 25
    search_fields = ("id", "email")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "password")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "email", "created_at", "updated_at")}),
        ("Auth", {"fields": ("password", "last_login")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser", "role")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
    )
    filter_horizontal = ("groups", "user_permissions")
```

Rules (per `dj-models`' admin conventions):

- `list_display` puts `id` first.
- `readonly_fields` includes `password` so the hashed value cannot be edited as text in the admin form. (Use `manage.py changepassword` or a custom action for password changes.)
- `fieldsets` separates Auth / Status / Permissions visually. The first fieldset (with `None` title) keeps identifiers and timestamps prominent.
- `filter_horizontal` on `groups` and `user_permissions` gives the standard dual-listbox UI, which scales better than the default multi-select widget.

## Step 9 — Verify

Non-interactive (CI / container init):

```bash
DJANGO_SUPERUSER_EMAIL=admin@example.test \
DJANGO_SUPERUSER_PASSWORD=changeme \
uv run python src/manage.py createsuperuser --noinput
```

Expected output: `Superuser created successfully.`

Interactive:

```bash
uv run python src/manage.py createsuperuser
```

The prompt asks for `Email:` and `Password:` (twice). On success, log in to `/admin/` with the new credentials.

Then run the project's verification gate:

```bash
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest
```

## Overrides

These hooks let a downstream project diverge cleanly without re-templating any file in this skill.

### Extending `Role`

A project that needs additional roles (e.g. `BILLING_ADMIN`, `READ_ONLY`) defines its own enum and rebinds the field's choices on the User model via a model override. Do not edit `accounts/enums.py` after the initial scaffold — extend it via the standard Python subclass pattern, or add new members in a project-specific migration.

### Service-layer routed creation

A project that requires policy checks before any user provisioning (e.g. tenant-scoped onboarding, MFA enrollment) subclasses `UserManager` in the project and rebinds `objects` on the User model:

```python
# src/accounts/managers.py (project-specific override)
class AppUserManager(UserManager):
    def create_superuser(self, email, password=None, **extra_fields):
        if not _policy_allows_superuser_creation():
            raise PermissionError("superuser creation requires explicit policy approval")
        return super().create_superuser(email, password, **extra_fields)
```

```python
# src/accounts/models.py
class User(AbstractBaseUser, PermissionsMixin):
    objects: ClassVar[AppUserManager] = AppUserManager()  # type: ignore[misc]
```

The pack's `UserManager` is the default; subclassing is the supported divergence path. Do NOT modify the pack's `UserManager` itself — that re-walks every project into the trap this skill exists to prevent.

### Adding required fields at `createsuperuser` time

Add the field to the model AND to `REQUIRED_FIELDS`:

```python
class User(AbstractBaseUser, PermissionsMixin):
    ...
    display_name = models.CharField(max_length=255)

    REQUIRED_FIELDS: ClassVar[list[str]] = ["display_name"]
```

Django will then prompt for `display_name` after `email` and `password` during interactive `createsuperuser`, and require `DJANGO_SUPERUSER_DISPLAY_NAME` env var under `--noinput`.

## Rules

- The User model is the **only** model in the project that ships a custom manager. `dj-models`' "no custom managers" rule has this single exception, because Django's `createsuperuser` requires it.
- Email is the natural key. Username is not used. Do not add a `username` field "for compatibility" — `USERNAME_FIELD = "email"` is the contract.
- `is_staff` is a custom `BooleanField` on the model. Do NOT inherit from `AbstractUser` (which provides `is_staff` for free) — that defeats the purpose of using `AbstractBaseUser` and re-imports the full `auth.User` surface this skill exists to avoid.
- `is_superuser`, `groups`, `user_permissions` come from `PermissionsMixin` — required for Django admin's permission checks.
- Never rename `Role` members in production. Add new members; deprecate old ones via documentation, not by rewriting strings.
- `AUTH_USER_MODEL` is set BEFORE the first `migrate`. After migrations exist, the swap is a multi-release cutover.
- Do not write `save()` overrides, `pre_save` signal handlers, or `@property` computed fields on the `User` model. The custom `UserManager` is the only allowed deviation from `dj-models`' "no business logic on models" rule.

## Checklist

- [ ] `generate_usr_id` registered in `src/project/ids.py`
- [ ] `accounts` app created and added to `INSTALLED_APPS`
- [ ] `Role(TextChoices)` defined with `SUPER_ADMIN` / `ADMIN` / `MEMBER` defaults
- [ ] `User(AbstractBaseUser, PermissionsMixin)` defined with `__prefix__ = "usr"`, ULID PK, email as `USERNAME_FIELD`, `is_active` + `is_staff` as custom `BooleanField`s, `role` field defaulting to `Role.MEMBER`
- [ ] `UserManager(BaseUserManager["User"])` defined with all four methods (`get_by_natural_key`, `_create_user`, `create_user`, `create_superuser`)
- [ ] `AUTH_USER_MODEL = "accounts.User"` set in `settings.py` BEFORE the first `migrate`
- [ ] Initial migration generated and applied
- [ ] Admin registered with `fieldsets` separating Auth / Status / Permissions and `filter_horizontal` on the m2m fields
- [ ] `createsuperuser --noinput` succeeds with `DJANGO_SUPERUSER_EMAIL` + `DJANGO_SUPERUSER_PASSWORD` env vars
- [ ] `ruff check` / `ruff format --check` / `pyrefly check` / `pytest` all pass
