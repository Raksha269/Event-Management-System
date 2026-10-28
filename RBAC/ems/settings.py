"""Minimal settings. If the team already has a settings.py, only copy the
lines marked  # RBAC  into it."""
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
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "ems.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": BASE_DIR / "db.sqlite3"}}  # PostgreSQL later

AUTH_USER_MODEL = "accounts.User"          # RBAC (must be set before 1st migrate)
LOGIN_URL = "/admin/login/"                # RBAC (replace with Auth team's login)

REST_FRAMEWORK = {                         # RBAC
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.EMSSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
STATIC_URL = "static/"
