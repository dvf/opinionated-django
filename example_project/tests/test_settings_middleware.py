"""Contract tests for the whitenoise middleware position and STORAGES backend.

These tests pin the dj-settings skill's `MIDDLEWARE` position contract and the
operator-ledger ADR 0004 decision (whitenoise as the default staticfiles
backend, non-manifest variant). A hand-edit that moves `WhiteNoiseMiddleware`
out of position, swaps to the manifest backend, or drops the DEBUG escape
hatches will trip these tests rather than waiting for an operator to notice
the admin rendering unstyled — or worse, CI silently breaking on the next
admin-touching test under `DEBUG=False`.
"""

from pathlib import Path

from django.conf import settings


SECURITY_MIDDLEWARE = "django.middleware.security.SecurityMiddleware"
SESSION_MIDDLEWARE = "django.contrib.sessions.middleware.SessionMiddleware"
WHITENOISE_MIDDLEWARE = "whitenoise.middleware.WhiteNoiseMiddleware"
WHITENOISE_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_MANIFEST_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "src" / "project" / "settings.py"


def test_whitenoise_middleware_is_installed():
    assert WHITENOISE_MIDDLEWARE in settings.MIDDLEWARE, (
        f"{WHITENOISE_MIDDLEWARE} must be in MIDDLEWARE — see ADR 0004 "
        "and the dj-settings skill MIDDLEWARE Position Contract."
    )


def test_whitenoise_middleware_immediately_follows_security_middleware():
    middleware = list(settings.MIDDLEWARE)
    security_index = middleware.index(SECURITY_MIDDLEWARE)
    whitenoise_index = middleware.index(WHITENOISE_MIDDLEWARE)
    assert whitenoise_index == security_index + 1, (
        f"WhiteNoiseMiddleware must be at position {security_index + 1} "
        f"(directly after SecurityMiddleware) but was at {whitenoise_index}. "
        "A misplaced middleware fails silently — the static-file shortcut is "
        "skipped and every request falls through to Django's view layer. See "
        "dj-settings MIDDLEWARE Position Contract."
    )


def test_whitenoise_middleware_precedes_session_middleware():
    middleware = list(settings.MIDDLEWARE)
    whitenoise_index = middleware.index(WHITENOISE_MIDDLEWARE)
    session_index = middleware.index(SESSION_MIDDLEWARE)
    assert whitenoise_index < session_index, (
        "WhiteNoiseMiddleware must precede SessionMiddleware so static-file "
        "requests do not unnecessarily open a session. See dj-settings "
        "MIDDLEWARE Position Contract."
    )


def test_staticfiles_storage_uses_whitenoise_compressed():
    backend = settings.STORAGES["staticfiles"]["BACKEND"]
    assert backend == WHITENOISE_STORAGE, (
        f"STORAGES['staticfiles']['BACKEND'] must be {WHITENOISE_STORAGE} "
        f"but was {backend}. See ADR 0004."
    )


def test_staticfiles_storage_is_not_manifest_variant():
    """Regression guard against the manifest variant.

    `CompressedManifestStaticFilesStorage` requires `collectstatic` to have run
    before any `DEBUG=False` request — otherwise it raises
    `ValueError: Missing staticfiles manifest entry for '<path>'` on every
    admin-touching test in CI. Manifest-mode is opt-in via a future ADR once
    the deploy pipeline has a real collectstatic step; until then, the pack
    default must remain the non-manifest variant. See ADR 0004 Consequences.
    """
    backend = settings.STORAGES["staticfiles"]["BACKEND"]
    assert "Manifest" not in backend, (
        f"STORAGES['staticfiles']['BACKEND'] is {backend} — the manifest "
        "variant ships a CI footgun (Missing staticfiles manifest entry under "
        "DEBUG=False without collectstatic) and is not the pack default. See "
        "ADR 0004 Consequences."
    )


def test_settings_file_does_not_reference_manifest_backend():
    """Belt-and-braces text guard against the manifest variant.

    Even a commented-out reference invites a future regression where someone
    uncomments. The scaffold's settings.py must not contain the manifest-backend
    string at all.
    """
    content = SETTINGS_PATH.read_text()
    assert WHITENOISE_MANIFEST_STORAGE not in content, (
        f"settings.py contains a reference to {WHITENOISE_MANIFEST_STORAGE}. "
        "The manifest backend is not the pack default — it requires "
        "collectstatic before any DEBUG=False boot. See ADR 0004 Consequences."
    )


def test_static_root_is_set():
    assert settings.STATIC_ROOT, (
        "STATIC_ROOT must be set so collectstatic has a destination and "
        "whitenoise has a directory to serve from."
    )


def test_debug_escape_hatches_present():
    """Under DEBUG, whitenoise must serve from app static/ dirs without
    requiring `collectstatic` between edits.
    """
    if not settings.DEBUG:
        return
    assert getattr(settings, "WHITENOISE_USE_FINDERS", False) is True, (
        "WHITENOISE_USE_FINDERS must be True under DEBUG so whitenoise serves "
        "from app static/ dirs without collectstatic. See ADR 0004."
    )
    assert getattr(settings, "WHITENOISE_AUTOREFRESH", False) is True, (
        "WHITENOISE_AUTOREFRESH must be True under DEBUG so whitenoise re-scans "
        "app static/ dirs between edits. See ADR 0004."
    )
