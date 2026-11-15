"""Loopback-only disposable benchmark settings, selected only by the staging runner."""
import os
from django.core.exceptions import ImproperlyConfigured
from .settings import *  # noqa: F403

if (os.environ.get("EMS_ISOLATED_STAGING") != "synthetic-only"
        or DATABASES["default"]["NAME"] not in {"ems_staging", "ems_restore_test"}
        or DATABASES["default"]["HOST"] != "127.0.0.1"
        or DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql"):
    raise ImproperlyConfigured("Staging settings require an isolated loopback PostgreSQL database.")
# No TLS proxy exists in the local harness; its HTTP socket binds only loopback.
DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
MEDIA_ROOT = BASE_DIR / ".staging" / "media"
STATIC_ROOT = BASE_DIR / ".staging" / "static"
