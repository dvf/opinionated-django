---
name: dj-auth
description: Install and wire authentication for a Django + Ninja project — custom User model (AbstractUser + email login + prefixed ULID PK), custom UserManager, AUTH_USER_MODEL, jwtninja for SPA/mobile API auth with Django sessions retained for admin, and AuthedRequest type narrowing. Use when scaffolding a new project that needs auth, or converting an existing Django project to the email-login + JWT pattern. Designed to pair with dj-scaffold and supersede its placeholder User import.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Install Auth for a Django + Ninja Project

This skill installs the authentication stack: a custom User model, email-based login, a `UserManager` that handles superuser creation cleanly, JWT auth for the Ninja API via `jwtninja`, Django session auth retained for the admin, and `AuthedRequest` type narrowing so handlers are fully typed.

**Critical prerequisite:** Django's `AUTH_USER_MODEL` MUST be set **before the first migration** runs. Retrofitting later is painful and requires data migration. Run this skill early in project scaffolding, before any `makemigrations` on app models that reference the User.

## BEFORE WRITING CODE

Read:

- `src/project/settings.py` — check if `AUTH_USER_MODEL` is already set, check `INSTALLED_APPS`
- `src/project/urls.py` — where to mount the auth router
- `src/project/api/__init__.py` — existing NinjaAPI and exception handlers
- `src/project/types.py` — `AuthedRequest` shape (this skill rewires it)
- Any existing User-related code — imports of `from django.contrib.auth.models import User` that will need updating

If `AUTH_USER_MODEL` is already set to something other than `"accounts.User"`, STOP and ask the user before proceeding — switching mid-project is a data-migration task.

---

## Dependencies

```bash
uv add jwtninja
```

`jwtninja` provides session-backed JWT auth for Django Ninja: every token references a DB `Session` row, which enables instant revocation, device tracking, and a per-token audit trail. Aligned with Ninja's type system — `AuthedRequest` narrows `request.auth.user` and `request.auth.session`.

**Maturity caveat:** `jwtninja` is pre-1.0 at time of writing. API may shift. Projects that need maximum stability over features may prefer the stateless `django-ninja-jwt` (SimpleJWT fork) — but lose the session-backed revocation and audit benefits. This skill ships `jwtninja` as the default because the session model is the better long-term fit for production apps; swap is straightforward if project needs diverge.

**Out of scope for this skill:** rate limiting on `/login/`. Wire it via `django-ratelimit`, a gateway (Cloudflare, API Gateway), or a dedicated middleware skill. Keeping it out keeps this skill focused on the auth contract, not denial-of-service hardening.

---

## The User Model

The custom User lives in an `accounts` app. If the app doesn't exist, create it first via `uv run python src/manage.py startapp accounts` and add it to `INSTALLED_APPS` as `"accounts.apps.AccountsConfig"`.

Per `dj-models`, `accounts/models/` is a directory, not a flat file.

### `src/accounts/models/user_manager.py`

```python
from __future__ import annotations

from typing import Any


class UserManager:
    """
    Custom manager for User with email as the unique identifier.

    Defined here so that accounts/models/user.py can import it cleanly.
    Inherits from BaseUserManager at attach time (see user.py).
    """

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
```

(In practice, inline this into `user.py` as a concrete `UserManager(BaseUserManager)` subclass — the split above is illustrative. The real file is below.)

### `src/accounts/models/user.py`

```python
from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from project.ids import generate_usr_id
from project.models import BaseModel


class UserManager(BaseUserManager):
    """Custom manager — email is the unique identifier, not username."""

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> User:
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uq_user_email"),
        ]

    __prefix__: ClassVar[str] = "usr"

    id = models.CharField(
        max_length=64, primary_key=True, default=generate_usr_id, editable=False
    )
    email = models.EmailField()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email
```

**Rules:**

1. **`AbstractUser`, not `AbstractBaseUser`.** Keeps Django's `is_staff`/`is_superuser`/`groups`/`user_permissions`/`last_login`/`date_joined` for free.
2. **`BaseModel` provides `created_at` / `updated_at` / `__prefix__` declaration.** See `dj-models` Base Model Inheritance.
3. **`id` is a prefixed ULID.** `usr_01jq...` — matches `dj-prefixed-ulids` across the whole project.
4. **`db_table = "users"`.** Override the default `accounts_user` — cleaner SQL, matches the verbose name.
5. **`USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`.** Email is the login identifier.
6. **`username` field stays** (inherited from `AbstractUser`). The `UserManager` sets `username = email` automatically. Dropping `username` requires `AbstractBaseUser` + reimplementing ~100 lines of permission machinery — not worth it.
7. **Email uniqueness in `Meta.constraints`, not `unique=True`** per `dj-models` Uniqueness rule.
8. **ID generator in `src/project/ids.py`:**
   ```python
   generate_usr_id = _make_generator("usr")
   ```

### `src/accounts/models/__init__.py`

```python
from .user import User, UserManager

__all__ = ["User", "UserManager"]
```

---

## Settings

In `src/project/settings.py`, add to the AUTH section:

```python
# =============================================================================
# AUTH
# =============================================================================
AUTH_USER_MODEL = "accounts.User"

# jwtninja — JWT auth for the Ninja API
from decouple import config

JWTNINJA_SIGNING_KEY = config("JWT_SIGNING_KEY")
JWTNINJA_ACCESS_TOKEN_LIFETIME_MINUTES = 20
JWTNINJA_REFRESH_TOKEN_LIFETIME_DAYS = 14
JWTNINJA_ROTATE_REFRESH_ON_USE = True
```

And to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    ...
    # Third-party
    "jwt_ninja",
    ...
    # Project apps
    "accounts.apps.AccountsConfig",
    ...
]
```

**Rules:**

1. **`AUTH_USER_MODEL` MUST be set before the first migration that creates the User table.** If migrations already exist for `accounts.User`, this is a no-op; if they exist for other apps with User FKs, retrofitting requires a data migration.
2. **Signing key from env.** `JWT_SIGNING_KEY` — never hard-coded. Separate from `SECRET_KEY` so rotating JWT signing doesn't invalidate Django sessions.
3. **Short access tokens + longer refresh.** 20 minutes / 14 days is the default; tune per project threat model.
4. **Refresh rotation on use** is the default — every `/refresh/` issues a new refresh and invalidates the old one.

---

## `AuthedRequest` Narrowing

Replace the placeholder `src/project/types.py` from `dj-scaffold` with the jwtninja-aware version:

```python
# src/project/types.py
from jwt_ninja.auth_classes import AuthedRequest, JWTAuth

__all__ = ["AuthedRequest", "JWTAuth"]
```

`AuthedRequest` narrows `request.auth.user` to an authenticated `User` and `request.auth.session` to the underlying `Session` row. Handlers that type their first arg as `AuthedRequest` get full IDE completion and pyrefly checks.

Any handler using `auth=JWTAuth()` on its router MUST type its first arg as `AuthedRequest` — not plain `HttpRequest`.

---

## Mounting the Auth Router

`jwtninja` provides the login / refresh / logout / sessions endpoints. Mount them under `/v1/auth/` in `src/project/api/__init__.py`:

```python
from jwt_ninja.routers import auth_router

api.add_router("/v1/auth", auth_router)
```

This gives you:

| Path | Method | Purpose |
|---|---|---|
| `/v1/auth/login/` | POST | Email + password → access + refresh, creates Session row |
| `/v1/auth/refresh/` | POST | Rotate tokens using refresh |
| `/v1/auth/logout/` | POST | Delete current session |
| `/v1/auth/logout-all/` | POST | Delete every session for the user |
| `/v1/auth/sessions/` | GET | List active sessions (device management) |

A `me` endpoint (returns the current user as a DTO) typically lives as a thin handler in your `users` router — not in the auth router — since it's about the user resource, not the auth flow.

---

## Django Admin Stays on Sessions

Do NOT disable Django's session middleware or auth backend globally. The admin is server-rendered and uses session auth. The split is clean:

- **Ninja API** (`/api/...`) → JWT auth via `JWTAuth()` on routers
- **Django admin** (`/admin/`) → session auth, unchanged from Django default

Both coexist because Django's session middleware only activates on requests it owns (admin, server-rendered views), and `JWTAuth()` on Ninja routers owns the API.

---

## User Admin

Per `dj-models` admin conventions, the User admin lives in `src/accounts/admin/user.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm

from accounts.models import User
from project.admin_utils import PrettyJSONMixin


@admin.register(User)
class UserAdmin(PrettyJSONMixin, BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_per_page = 25
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("id", "last_login", "date_joined", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Role & Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined", "created_at", "updated_at"),
        }),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )
    change_password_form = AdminPasswordChangeForm
```

**Rules:**

1. **Inherit from `BaseUserAdmin`**, not `admin.ModelAdmin` — preserves the password-change flow and other admin conveniences.
2. **Fieldsets follow the three-band pattern** from `dj-models` (None → named sections → "Important Dates" last).
3. **`add_fieldsets`** is the "Add user" form — just email + password. Other fields filled in after creation.
4. **`PrettyJSONMixin` first in MRO** — per `dj-models` admin utility rules, in case any future User field is a JSONField.

---

## Tests

Tests live at `tests/accounts/test_api.py` and follow the three-layer convention from `dj-pytest`:

```python
import pytest


@pytest.mark.django_db
def test_login_returns_tokens(client):
    from accounts.models import User

    user = User.objects.create_user(email="user@example.com", password="pw12345!")

    response = client.post(
        "/api/v1/auth/login/",
        data={"email": "user@example.com", "password": "pw12345!"},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body
    assert "refresh" in body


@pytest.mark.django_db
def test_login_rejects_wrong_password(client):
    from accounts.models import User

    User.objects.create_user(email="user@example.com", password="pw12345!")

    response = client.post(
        "/api/v1/auth/login/",
        data={"email": "user@example.com", "password": "wrong"},
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_rotates_token(client):
    # ... login, capture refresh, POST /refresh/, assert new refresh != old refresh
    ...


@pytest.mark.django_db
def test_logout_revokes_session(client):
    # ... login, capture access, POST /logout/, hit /sessions/ with access, assert 401
    ...
```

---

## Verify

```bash
uv run python src/manage.py makemigrations accounts
uv run python src/manage.py migrate
uv run ruff check src
uv run ruff format --check src
uv run pyrefly check src
uv run pytest tests/accounts
```

All must pass. The migration step creates the `users` table with the ULID PK.

Create a superuser to confirm the email-login manager works:

```bash
uv run python src/manage.py createsuperuser --email admin@example.com
```

---

## Checklist

- [ ] `jwtninja` installed via `uv add`
- [ ] `accounts` app created and listed in `INSTALLED_APPS`
- [ ] `src/project/ids.py` has `generate_usr_id = _make_generator("usr")`
- [ ] `src/accounts/models/user.py` defines `User(AbstractUser, BaseModel)` with ULID PK, email login, UserManager
- [ ] `AUTH_USER_MODEL = "accounts.User"` set in settings BEFORE first migration
- [ ] `JWT_SIGNING_KEY` read from env; access/refresh lifetimes configured
- [ ] `src/project/types.py` imports `AuthedRequest`, `JWTAuth` from `jwt_ninja.auth_classes`
- [ ] `/v1/auth/` router mounted in `src/project/api/__init__.py`
- [ ] `src/accounts/admin/user.py` registers User with three-band fieldsets and `add_fieldsets`
- [ ] Django admin still works via session auth (not disabled)
- [ ] Migrations generated and applied
- [ ] Tests for login / wrong-password / refresh rotation / logout all pass
- [ ] `createsuperuser` works with `--email`
