---
name: dj-settings
description: Organize Django settings.py into clearly sectioned blocks with banner-style headers. Use proactively whenever modifying src/project/settings.py — adding new settings, removing settings, or restructuring sections.
allowed-tools: Read, Edit
---

# Organize Django Settings

When modifying `src/project/settings.py`, enforce this structure.

## Section Format

Every logical group of settings gets a banner header:

```python
# =============================================================================
# SECTION NAME
# =============================================================================
```

- Banner lines are exactly 77 characters (`# ` + 75 `=` characters)
- Section name is UPPERCASE
- One blank line before each banner (except at top of file)
- No blank lines between the banner and the first setting in that section
- No inline comments explaining what standard Django settings do — the section header is enough

## Section Order

Settings must appear in this order. Omit sections that have no settings.

1. **Imports and `BASE_DIR`** (no banner — these are preamble)
2. **LOGGING**
3. **SECURITY** — `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS, CSRF, cookie settings
4. **APPLICATION DEFINITION** — `INSTALLED_APPS`, `MIDDLEWARE`
5. **URLS AND WSGI** — `ROOT_URLCONF`, `WSGI_APPLICATION`
6. **TEMPLATES**
7. **AUTH** — `AUTH_USER_MODEL`, `AUTH_PASSWORD_VALIDATORS`, `LOGIN_URL`
8. **DATABASE**
9. **SESSIONS**
10. **CACHING**
11. **INTERNATIONALIZATION** — `LANGUAGE_CODE`, `TIME_ZONE`, `USE_I18N`, `USE_TZ`
12. **STATIC FILES** — `STATIC_URL`, `STATIC_ROOT`, `STORAGES`, `DEFAULT_AUTO_FIELD`
13. **CELERY** — all `CELERY_*` settings
14. Any additional project-specific sections in alphabetical order

## `INSTALLED_APPS` Sub-grouping

Within `INSTALLED_APPS`, group entries with inline comments:

```python
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    ...
    # Third-party
    "corsheaders",
    ...
    # Project apps
    "products.apps.ProductsConfig",
    "orders.apps.OrdersConfig",
]
```

Project apps must use the dotted path to their `AppConfig` subclass (e.g., `"myapp.apps.MyAppConfig"`), not the short app name.

## `MIDDLEWARE` Position Contract

`whitenoise.middleware.WhiteNoiseMiddleware` MUST appear **immediately after** `django.middleware.security.SecurityMiddleware` and **before** `django.contrib.sessions.middleware.SessionMiddleware`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

This position is non-negotiable: whitenoise must run after security headers are applied but before anything that could short-circuit the response or open a session. A misplaced `WhiteNoiseMiddleware` fails silently — the static-file shortcut is skipped and every request falls through to Django's view layer, so the symptom is "everything is slower" rather than a loud error. The position is enforced by a contract test (`example_project/tests/test_settings_middleware.py`).

In the STATIC FILES section, pair this with:

```python
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

if DEBUG:
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True
```

`CompressedStaticFilesStorage` gives gzip + brotli precompression without filename hashing or a `staticfiles.json` manifest. `STATIC_ROOT` MUST be set (e.g., `BASE_DIR / "staticfiles"`) so `collectstatic` has somewhere to write — whitenoise serves from `STATIC_ROOT`, not from each app's `static/` directory. Under `DEBUG`, `WHITENOISE_USE_FINDERS = True` + `WHITENOISE_AUTOREFRESH = True` let whitenoise serve and re-scan app `static/` dirs without re-running `collectstatic` between edits.

**Do NOT use `CompressedManifestStaticFilesStorage`.** The manifest variant hashes filenames and emits a `staticfiles.json` that is **required** at request time — without it, the storage class raises `ValueError: Missing staticfiles manifest entry for '<path>'` on any `DEBUG=False` request that touches a static-asset URL (e.g., every admin login page). That blows up CI suites that exercise `DEBUG=False` branches without running `collectstatic` first, and 500s any deploy whose pipeline hasn't been wired with a `collectstatic` step. Manifest-mode is a real production cache-busting gain, but it is opt-in via a future ADR once the deploy pipeline has a real `collectstatic` step. The contract test in `example_project/tests/test_settings_middleware.py` fails if the scaffolded settings.py references the manifest variant at all.

The rationale for shipping whitenoise by default is in operator ledger ADR 0004.

## Rules

- Do NOT add Django docs URLs as comments (e.g., `# https://docs.djangoproject.com/...`)
- Do NOT add "Quick-start" or "Generated by" boilerplate comments
- Keep `AUTH_PASSWORD_VALIDATORS` compact — one dict per line when the only key is `"NAME"`
- When adding a new setting, place it in the correct existing section. Create a new section only if none fit.
