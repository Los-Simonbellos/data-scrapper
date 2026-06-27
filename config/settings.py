"""
Minimal Django settings for the registro-pacientes scraping service.

This service does NOT use the Django ORM or a database — it is a thin,
stateless API in front of the public Supabase backend that powers
https://registro-pacientes-sismo-vzla.pages.dev/. Keep it lean so it
cold-starts fast on Vercel serverless.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = _env_bool("DJANGO_DEBUG", True)

# Vercel serves from an arbitrary *.vercel.app host, so allow all.
# (No cookies/sessions are issued, so host validation buys us little here.)
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"]

INSTALLED_APPS = [
    "pacientes",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.app"

# No templates / no DB needed.
TEMPLATES = []
DATABASES = {}

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Caracas"
USE_I18N = False
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ---------------------------------------------------------------------------
# Service configuration
# ---------------------------------------------------------------------------
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://ghswopasaynslycpaldj.supabase.co"
).rstrip("/")
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdoc3dvcGFzYXluc2x5Y3BhbGRqIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODI0MDU0MDcsImV4cCI6MjA5Nzk4MTQwN30."
    "MifuBb6C54KQdhuv_4gMoNAGJl997ycU299OcFeoyzU",
)
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "pacientes")

# API-key gate. Comma-separated keys callers send via the `X-API-Key`
# header (or `Authorization: Bearer <key>`).
SERVICE_API_KEYS = [
    k.strip() for k in os.environ.get("SERVICE_API_KEYS", "").split(",") if k.strip()
]
# When true, requests are rejected unless a valid key is supplied. With no
# keys configured this fails closed (everything 401), preventing an
# accidentally open deploy. When false, an empty SERVICE_API_KEYS means the
# endpoint stays open.
SERVICE_REQUIRE_API_KEY = _env_bool("SERVICE_REQUIRE_API_KEY", False)
