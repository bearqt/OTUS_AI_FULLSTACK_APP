from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
  "django.contrib.admin",
  "django.contrib.auth",
  "django.contrib.contenttypes",
  "django.contrib.sessions",
  "django.contrib.messages",
  "django.contrib.staticfiles",
  "corsheaders",
  "rest_framework",
  "rest_framework.authtoken",
  "django_filters",
  "drf_spectacular",
  "apps.users",
  "apps.kanban",
]

MIDDLEWARE = [
  "corsheaders.middleware.CorsMiddleware",
  "django.middleware.security.SecurityMiddleware",
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
  }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("POSTGRES_DB"):
  DATABASES = {
    "default": {
      "ENGINE": "django.db.backends.postgresql",
      "NAME": os.getenv("POSTGRES_DB", "minitrello"),
      "USER": os.getenv("POSTGRES_USER", "postgres"),
      "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
      "HOST": os.getenv("POSTGRES_HOST", "db"),
      "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
  }
else:
  DATABASES = {
    "default": {
      "ENGINE": "django.db.backends.sqlite3",
      "NAME": BASE_DIR / "db.sqlite3",
    }
  }

AUTH_PASSWORD_VALIDATORS = [
  {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
  {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
  {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
  "DEFAULT_AUTHENTICATION_CLASSES": (
    "rest_framework_simplejwt.authentication.JWTAuthentication",
  ),
  "DEFAULT_PERMISSION_CLASSES": (
    "rest_framework.permissions.IsAuthenticated",
  ),
  "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
  "DEFAULT_FILTER_BACKENDS": (
    "django_filters.rest_framework.DjangoFilterBackend",
    "rest_framework.filters.SearchFilter",
    "rest_framework.filters.OrderingFilter",
  ),
  "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
  "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
  "TITLE": "MiniTrello API",
  "DESCRIPTION": "Backend API for MiniTrello training project",
  "VERSION": "1.0.0",
  "SERVE_INCLUDE_SCHEMA": False,
  "COMPONENT_SPLIT_REQUEST": True,
  "SWAGGER_UI_SETTINGS": {
    "deepLinking": True,
    "persistAuthorization": True,
  },
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
  "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
  "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
  "AUTH_HEADER_TYPES": ("Bearer",),
}

cors_origins = os.getenv(
  "CORS_ALLOWED_ORIGINS",
  "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins.split(",") if o.strip()]

