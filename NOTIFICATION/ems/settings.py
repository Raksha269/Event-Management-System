"""Minimal standalone settings. When merging into the main project, copy only
the lines marked  # NOTIFICATIONS."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "dev-only-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "notifications",   # NOTIFICATIONS
    "standins",        # TEMPORARY: remove once real Event/Registration models exist
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "ems.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": BASE_DIR / "db.sqlite3"}}   # PostgreSQL later
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"

# --- NOTIFICATIONS -----------------------------------------------------------
# Provider-neutral: the default sends through Django's email system, so SendGrid
# or SES SMTP works by changing EMAIL_* settings only.
NOTIFICATION_EMAIL_BACKEND = "notifications.email_service.DjangoMailBackend"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"   # dev: print to terminal
DEFAULT_FROM_EMAIL = "EMS <no-reply@ems.example>"
SUPPORT_EMAIL = "support@ems.example"
SITE_URL = "http://localhost:8000"

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
CELERY_BEAT_SCHEDULE = {
    "ems-reminders-every-5-min": {
        "task": "notifications.tasks.run_scheduled_notifications",
        "schedule": 300.0,
    },
}

if "test" in sys.argv:   # tests: no Redis, no real email
    NOTIFICATION_EMAIL_BACKEND = "notifications.email_service.MockEmailBackend"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
