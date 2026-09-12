import os
from datetime import timedelta
from pathlib import Path

import sentry_sdk
from botocore.client import Config
from celery.schedules import crontab
from corsheaders.defaults import default_headers
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

load_dotenv()

# * Environment
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

REDIS_HOST = os.getenv("REDIS")
if not REDIS_HOST:
    raise ValueError("REDIS_HOST is not set!")

REDIS = REDIS_HOST
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_TOKEN_ADMIN = os.getenv("TELEGRAM_BOT_TOKEN_ADMIN")
SENTRY_DSN = os.getenv("SENTRY_DSN")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
TIME_ZONE = os.getenv("TZ")

# * Base
BASE_DIR = Path(__file__).resolve().parent.parent

SHOP_CONFIG_DIR = "/app/shop_config"

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

ROOT_URLCONF = "config.urls"

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
    ("es", "Español"),
    ("uk", "Українська"),
    ("cs", "Čeština"),
    ("de", "Deutsch"),
]

USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locales",
]

raw_hosts = (
    f"127.0.0.1,localhost,backend,{os.getenv('FRONTEND_VIRTUAL_HOST', '')},{os.getenv('BACKEND_VIRTUAL_HOST', '')}"
)
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]

if DEBUG:
    ALLOWED_HOSTS += "127.0.0.1,localhost,backend,.ngrok-free.app,.ngrok-free.dev".split(",")


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# * Apps django and user apps
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.users",
    "apps.catalog",
    "apps.orders",
    "apps.payments",
    "apps.telegram",
    "apps.basket",
    "apps.delivery",
    "apps.notifications",
    "apps.support",
]


# * Middleware and templates
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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


# * WSGI and ASGI
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# * Databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TEST": {
            "NAME": os.getenv("POSTGRES_DB"),
            "HOST": "db",
            "PORT": os.getenv("POSTGRES_PORT"),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# * Media and Static
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
UPLOADED_FILES_USE_URL = False

USE_S3 = True

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")

AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_ADDRESSING_STYLE = "path"

AWS_S3_CLIENT_CONFIG = Config(
    region_name=AWS_S3_REGION_NAME,
    signature_version="s3v4",
    s3={"addressing_style": "path"},
)

AWS_DEFAULT_ACL = None
AWS_S3_BUCKET_AUTH_PRERESOURCE = False

AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")

AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}

AWS_LOCATION = "media"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

WHITENOISE_ROOT = BASE_DIR / "static" / "root"

# * Celery and Redis
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:6379/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}


# * Setting Celery Beat
CELERY_BEAT_SCHEDULE = {
    "cleanup-django-sessions-nightly": {
        "task": "core.cleanup_django_sessions_task",
        "schedule": crontab(hour=3, minute=0),
    },
    "clear-discounts-every-hour": {
        "task": "catalog.cleanup_expired_discounts",
        "schedule": crontab(minute=0),
    },
    "cleanup_old_closed_topics": {
        "task": "support.cleanup_old_closed_topics",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
}


# * Cors and rest settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    ngrok_domain = os.getenv("NGROK_STATIC_DOMAIN", "").strip()
    if ngrok_domain:
        CSRF_TRUSTED_ORIGINS.append(f"https://{ngrok_domain}")
else:

    def format_origin(host):
        host = host.strip()
        if host and not host.startswith(("http://", "https://")):
            return f"https://{host}"
        return host

    raw_frontend = os.getenv("FRONTEND_VIRTUAL_HOST", "").split(",")
    raw_backend = os.getenv("BACKEND_VIRTUAL_HOST", "").split(",")

    formatted_frontend_hosts = [format_origin(h) for h in raw_frontend if h.strip()]
    formatted_backend_hosts = [format_origin(h) for h in raw_backend if h.strip()]

    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ] + formatted_frontend_hosts

    CSRF_TRUSTED_ORIGINS = formatted_frontend_hosts + formatted_backend_hosts

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    *default_headers,
    "ngrok-skip-browser-warning",
)

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.domain.exceptions.custom_exception_handler",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "tg_id",
    "USER_ID_CLAIM": "user_id",
}


# * Spectular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Web telergram shop API",
    "DESCRIPTION": "Telegram Mini App API with cryptocurrency payments",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}


# * Loggings Sentry settings
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment="development" if DEBUG else "production",
        traces_sample_rate=1.0,
        send_default_pii=True,
        enable_logs=True,
    )

# * Admin panel unfold
if DEBUG:
    current_url = f"https://{os.getenv('NGROK_STATIC_DOMAIN', '').strip()}"
else:
    current_url = f"https://{os.getenv('FRONTEND_VIRTUAL_HOST', '').split(',')[0]}"

UNFOLD = {
    "SITE_TITLE": "Telegram Shop Admin",
    "SITE_HEADER": _("Store management"),
    "SITE_URL": current_url,
    "SHOW_LANGUAGES": True,
    "SITE_ICON": {
        "light": lambda request: "/favicon.svg",
        "dark": lambda request: "/favicon.svg",
    },
}

UNFOLD_I18N_STRINGS = [
    _("Type to search"),
    _("Search"),
    _("Filters"),
    _("Navigation"),
]

# * Emails
if os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
