import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "local").strip().casefold()
DEPLOYMENT_COMMIT_SHA = os.getenv("RAILWAY_GIT_COMMIT_SHA", "").strip()
DEPLOYMENT_GIT_BRANCH = os.getenv("RAILWAY_GIT_BRANCH", "").strip()
DEPLOYMENT_ENVIRONMENT = (
    os.getenv("RAILWAY_ENVIRONMENT_NAME", "").strip() or DJANGO_ENV
)
DEPLOYMENT_SERVICE = os.getenv("RAILWAY_SERVICE_NAME", "").strip()
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-only-insecure-key")
if DJANGO_ENV in {"staging", "production"} and SECRET_KEY == "local-only-insecure-key":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY es obligatorio fuera de local.")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
RAILWAY_HEALTHCHECK_HOST = "healthcheck.railway.app"
if RAILWAY_HEALTHCHECK_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_HEALTHCHECK_HOST)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "csp",
    "branding",
    "catalog",
    "campaigns",
    "briefs",
    "designs.apps.DesignsConfig",
    "ai",
    "assets",
    "validations",
    "security",
    "materials",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.CorrelationIdMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend", BASE_DIR / "frontend" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": ["common.templatetags.frontend_assets"],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

def _database_from_url(database_url: str) -> dict:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL debe usar el esquema postgres:// o postgresql://.")
    query = parse_qs(parsed.query)
    options = {
        key: values[-1]
        for key, values in query.items()
        if key in {"sslmode", "connect_timeout"} and values
    }
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or "5432"),
        "OPTIONS": options,
    }


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
elif DB_ENGINE == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "ih_design"),
            "USER": os.getenv("POSTGRES_USER", "ih_design"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_THROTTLE_RATE = os.getenv("LOGIN_THROTTLE_RATE", "10/hour")

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["security.permissions.CorporateDomainPermission"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_THROTTLE_RATES": {
        "login_ip": LOGIN_THROTTLE_RATE,
    },
}

def _env_list(name: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())


CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"
SESSION_COOKIE_SECURE = os.getenv("DJANGO_SECURE_COOKIES", "0") == "1"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "0"))
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    }
}

CORPORATE_AUTH_REQUIRED = os.getenv("DJANGO_REQUIRE_CORPORATE_AUTH", "1") == "1"
CORPORATE_ALLOWED_EMAIL_DOMAINS = tuple(
    domain.strip().casefold().lstrip("@").rstrip(".")
    for domain in os.getenv(
        "CORPORATE_ALLOWED_EMAIL_DOMAINS",
        "ihmexico.com,ihbogota.com,ihsantiago.cl,ihlima.com",
    ).split(",")
    if domain.strip()
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
AI_ROUTER_ENABLED = os.getenv("AI_ROUTER_ENABLED", "0") == "1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
ANTHROPIC_TIMEOUT_SECONDS = float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "45"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
PASSWORD_RESET_MAX_AGE_SECONDS = int(os.getenv("PASSWORD_RESET_MAX_AGE_SECONDS", "900"))
DESIGN_TEST_MODE = os.getenv("DESIGN_TEST_MODE", "1") == "1"
DESIGN_TEST_LIMIT = int(os.getenv("DESIGN_TEST_LIMIT", "50"))
DESIGN_TEST_ALLOW_HUMAN_APPROVAL = (
    os.getenv("DESIGN_TEST_ALLOW_HUMAN_APPROVAL", "0") == "1"
)
if DJANGO_ENV == "production" and DESIGN_TEST_ALLOW_HUMAN_APPROVAL:
    raise ImproperlyConfigured(
        "DESIGN_TEST_ALLOW_HUMAN_APPROVAL solo puede activarse fuera de production."
    )

AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    # Vacío = AWS S3 real (boto3 resuelve el endpoint por región); con valor = proveedor
    # S3-compatible (Backblaze, DigitalOcean Spaces, etc.).
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL") or None
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
