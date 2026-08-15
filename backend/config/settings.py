import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "local").strip().casefold()
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
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
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

HUB_OIDC_ENABLED = os.getenv("HUB_OIDC_ENABLED", "0") == "1"
HUB_OIDC_PRODUCTION_APPROVED = os.getenv("HUB_OIDC_PRODUCTION_APPROVED", "0") == "1"
HUB_OIDC_ISSUER = os.getenv("HUB_OIDC_ISSUER", "").strip().rstrip("/")
HUB_OIDC_CLIENT_ID = os.getenv("HUB_OIDC_CLIENT_ID", "").strip()
HUB_OIDC_CLIENT_SECRET = os.getenv("HUB_OIDC_CLIENT_SECRET", "").strip()
HUB_OIDC_REDIRECT_URI = os.getenv("HUB_OIDC_REDIRECT_URI", "").strip()
HUB_OIDC_SESSION_MAX_AGE_SECONDS = int(os.getenv("HUB_OIDC_SESSION_MAX_AGE_SECONDS", "900"))
HUB_OIDC_STATE_MAX_AGE_SECONDS = int(os.getenv("HUB_OIDC_STATE_MAX_AGE_SECONDS", "600"))
HUB_OIDC_CLOCK_SKEW_SECONDS = int(os.getenv("HUB_OIDC_CLOCK_SKEW_SECONDS", "30"))

if HUB_OIDC_ENABLED:
    required_hub_oidc_settings = {
        "HUB_OIDC_ISSUER": HUB_OIDC_ISSUER,
        "HUB_OIDC_CLIENT_ID": HUB_OIDC_CLIENT_ID,
        "HUB_OIDC_CLIENT_SECRET": HUB_OIDC_CLIENT_SECRET,
        "HUB_OIDC_REDIRECT_URI": HUB_OIDC_REDIRECT_URI,
    }
    missing_hub_oidc_settings = [
        name for name, value in required_hub_oidc_settings.items() if not value
    ]
    if missing_hub_oidc_settings:
        raise ImproperlyConfigured(
            "Configuración OIDC incompleta: " + ", ".join(missing_hub_oidc_settings)
        )
    if len(HUB_OIDC_CLIENT_SECRET) < 32:
        raise ImproperlyConfigured("HUB_OIDC_CLIENT_SECRET debe tener al menos 32 caracteres.")
    if DJANGO_ENV != "local":
        oidc_urls = {
            "HUB_OIDC_ISSUER": urlparse(HUB_OIDC_ISSUER),
            "HUB_OIDC_REDIRECT_URI": urlparse(HUB_OIDC_REDIRECT_URI),
        }
        invalid_oidc_urls = [
            name
            for name, parsed in oidc_urls.items()
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password
        ]
        if invalid_oidc_urls:
            raise ImproperlyConfigured(
                "Issuer y callback OIDC deben ser URLs HTTPS absolutas fuera de local: "
                + ", ".join(invalid_oidc_urls)
            )
    if DJANGO_ENV == "production" and not HUB_OIDC_PRODUCTION_APPROVED:
        raise ImproperlyConfigured(
            "HUB_OIDC_PRODUCTION_APPROVED debe habilitarse explícitamente en Producción."
        )
    if not 60 <= HUB_OIDC_SESSION_MAX_AGE_SECONDS <= 900:
        raise ImproperlyConfigured(
            "HUB_OIDC_SESSION_MAX_AGE_SECONDS debe estar entre 60 y 900 segundos."
        )
    if not 60 <= HUB_OIDC_STATE_MAX_AGE_SECONDS <= 600:
        raise ImproperlyConfigured(
            "HUB_OIDC_STATE_MAX_AGE_SECONDS debe estar entre 60 y 600 segundos."
        )
    if not 0 <= HUB_OIDC_CLOCK_SKEW_SECONDS <= 60:
        raise ImproperlyConfigured("HUB_OIDC_CLOCK_SKEW_SECONDS debe estar entre 0 y 60.")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
ANTHROPIC_TIMEOUT_SECONDS = float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "45"))
POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN", "").strip()
POSTMARK_FROM_EMAIL = os.getenv("POSTMARK_FROM_EMAIL", "mydesign@ihlatam.com").strip()
POSTMARK_FROM_NAME = os.getenv("POSTMARK_FROM_NAME", "IH Design").strip()
POSTMARK_MESSAGE_STREAM = os.getenv("POSTMARK_MESSAGE_STREAM", "outbound").strip()
POSTMARK_REPLY_TO = os.getenv("POSTMARK_REPLY_TO", "").strip()
EMAIL_DELIVERY_MODE = os.getenv("EMAIL_DELIVERY_MODE", "disabled").strip().casefold()
EMAIL_ALLOWED_RECIPIENTS = tuple(
    value.strip().casefold()
    for value in os.getenv("EMAIL_ALLOWED_RECIPIENTS", "").split(",")
    if value.strip()
)
if EMAIL_DELIVERY_MODE not in {"disabled", "allowlist", "live"}:
    raise ImproperlyConfigured("EMAIL_DELIVERY_MODE debe ser disabled, allowlist o live.")
if EMAIL_DELIVERY_MODE == "live" and DJANGO_ENV != "production":
    raise ImproperlyConfigured(
        "EMAIL_DELIVERY_MODE=live solo está permitido con DJANGO_ENV=production."
    )
PASSWORD_RESET_MAX_AGE_SECONDS = int(os.getenv("PASSWORD_RESET_MAX_AGE_SECONDS", "900"))
DESIGN_TEST_MODE = os.getenv("DESIGN_TEST_MODE", "1") == "1"
DESIGN_TEST_LIMIT = int(os.getenv("DESIGN_TEST_LIMIT", "50"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        # Authlib debug output includes ephemeral PKCE values; never emit it.
        "authlib": {"level": "WARNING"},
    },
}

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
