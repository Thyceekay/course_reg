"""Environment-based Django configuration for local SQLite and Render PostgreSQL."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

# Never fall back to a checked-in or generated secret key.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before starting the application.")

# Debug is off by default so an unset variable cannot expose debug pages.
DEBUG = os.environ.get("DJANGO_DEBUG", "False").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Production hosts must be configured explicitly; local development has safe defaults.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
elif not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS for non-debug environments.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite is local-only; production must explicitly provide PostgreSQL credentials.
DATABASE_ENGINE = os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower()
DATABASE_SSL_REQUIRE = os.environ.get(
    "DATABASE_SSL_REQUIRE", str(not DEBUG)
).strip().lower() in {"1", "true", "yes", "on"}
if DATABASE_ENGINE == "sqlite":
    if not DEBUG:
        raise ImproperlyConfigured(
            "SQLite is for local development; configure PostgreSQL outside debug mode."
        )
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif DATABASE_ENGINE == "postgresql":
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        database_config = dj_database_url.parse(
            database_url,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=DATABASE_SSL_REQUIRE,
        )
        if database_config["ENGINE"] != "django.db.backends.postgresql":
            raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL.")
        DATABASES = {"default": database_config}
    else:
        required_database_variables = (
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
        )
        missing_database_variables = [
            variable
            for variable in required_database_variables
            if not os.environ.get(variable)
        ]
        if missing_database_variables:
            missing = ", ".join(missing_database_variables)
            raise ImproperlyConfigured(
                f"Set DATABASE_URL or the PostgreSQL environment variables: {missing}."
            )
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ["POSTGRES_DB"],
                "USER": os.environ["POSTGRES_USER"],
                "PASSWORD": os.environ["POSTGRES_PASSWORD"],
                "HOST": os.environ["POSTGRES_HOST"],
                "PORT": os.environ.get("POSTGRES_PORT", "5432"),
                "CONN_MAX_AGE": 600,
                "CONN_HEALTH_CHECKS": True,
                "OPTIONS": {"sslmode": "require"} if DATABASE_SSL_REQUIRE else {},
            }
        }
else:
    raise ImproperlyConfigured(
        "DATABASE_ENGINE must be either 'sqlite' or 'postgresql'."
    )

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

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "admin:index"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Render terminates TLS and forwards the original protocol to the application.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get(
    "DJANGO_SECURE_SSL_REDIRECT",
    str(not DEBUG),
).strip().lower() in {"1", "true", "yes", "on"}
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
