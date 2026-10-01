"""
Django settings for the SRIP (Student Research Internship Portal) backend.

Phase 1 scope: postings, applications, admission workflow, notifications.
No Anumati integration in this phase -- see applications/hooks.py for the
seam where Phase 2 will attach.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "users",
    "postings",
    "applications",
    "notifications",
    "anumati_integration",
    "agents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "srip.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "srip.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
if os.getenv("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(os.getenv("DATABASE_URL"))

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# --- Phase 2: Anumati integration -------------------------------------
# ANUMATI_MOCK=True (the default) means anumati_integration/hooks calls use
# MockAnumatiClient -- no network calls, safe for local dev and CI. Set to
# False and provide real credentials to talk to an actual Anumati instance.
#
# As of 2026-08-06, ANUMATI_BASE_URL should point at the
# DPI-Primitive-Jenkins-dev backend (JWT bearer auth, namespaced endpoints
# under /auth/, /locker/, /connectionType/, /connection/) -- confirmed live,
# see anumati_integration/client.py's module docstring and
# docs/sprint-8-locker-linking.md. The older root-mounted, HTTP-Basic-auth
# API this was originally built against is no longer what's deployed.
ANUMATI_MOCK = os.getenv("ANUMATI_MOCK", "True") == "True"
ANUMATI_BASE_URL = os.getenv("ANUMATI_BASE_URL", "http://localhost:9000")
ANUMATI_HOST_USERNAME = os.getenv("ANUMATI_HOST_USERNAME", "")
ANUMATI_HOST_PASSWORD = os.getenv("ANUMATI_HOST_PASSWORD", "")

# The real, human-facing Anumati portal opened in a new tab for the
# legacy self-attested linking path (student, no OAuth yet). Kept as a
# fallback -- see docs/oauth-locker-linking.md for why the OAuth flow
# below is now the primary path.
ANUMATI_PORTAL_URL = os.getenv("ANUMATI_PORTAL_URL", "https://anumati.iiitb.ac.in/login")

# OAuth-style locker linking (see anumati_integration/views.py:
# oauth_start / oauth_callback, and docs/oauth-locker-linking.md). SRIP is
# registered as a "relying app" on the Anumati side via its own
# `create_oauth_client` management command, which prints these values once.
ANUMATI_OAUTH_CLIENT_ID = os.getenv("ANUMATI_OAUTH_CLIENT_ID", "srip")
ANUMATI_OAUTH_CLIENT_SECRET = os.getenv("ANUMATI_OAUTH_CLIENT_SECRET", "")
# Must exactly match a redirect_uri registered for this client_id on the
# Anumati side -- Anumati rejects the authorize request otherwise.
ANUMATI_OAUTH_REDIRECT_URI = os.getenv(
    "ANUMATI_OAUTH_REDIRECT_URI", "http://localhost:8000/api/anumati/oauth/callback/"
)
# Where SRIP's frontend lands after a successful/failed link, so the user
# ends up back in the app, not on a bare JSON response.
ANUMATI_OAUTH_FRONTEND_RETURN_URL = os.getenv(
    "ANUMATI_OAUTH_FRONTEND_RETURN_URL", "http://localhost:5173/anumati"
)

# Symmetric key used to encrypt each Institution's own Anumati password at
# rest (see users/models.py, Institution.set_anumati_password). Anumati's
# 2026-08-06 backend moved to JWT bearer auth (see ANUMATI_BASE_URL comment
# above) -- SRIP no longer sends a raw password on every single request,
# only when logging in for a fresh access token -- but SRIP still has no
# scoped service-account/OAuth2-client-credentials mode to use instead, so
# the institution's real password still has to be stored somewhere to log
# in again later. This is a stopgap for that reason, not the request-level
# one. It goes away entirely if Anumati adds a service-account mode.
# Generate a real key for anything beyond local dev with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ANUMATI_CREDENTIAL_KEY = (
    os.getenv("ANUMATI_CREDENTIAL_KEY") or "-VkrkNv3T-EaQqo9h8ADoJ8URrrvYzqIX1EZc1INcqU="
)

# --- Agent environment -------------------------------------------------
# OpenAI-compatible endpoint used by the three initial SaRaDE agents.
# Leave unset to disable agent calls without breaking the rest of SRIP.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
