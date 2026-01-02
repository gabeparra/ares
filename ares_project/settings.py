"""
Django settings for ARES project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DEBUG', 'False') == 'True'  # Default to False for security

# SECURITY: SECRET_KEY should be set via environment variable
# In development, we allow a default. In production, it's required.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        import warnings
        warnings.warn("Using default SECRET_KEY in development. Set DJANGO_SECRET_KEY in production!")
        SECRET_KEY = 'django-insecure-dev-only-change-in-production'
    else:
        import sys
        print("ERROR: DJANGO_SECRET_KEY environment variable is required in production")
        print("Generate with: python -c \"import secrets; print(secrets.token_urlsafe(50))\"")
        sys.exit(1)

# SECURITY: Encryption key for sensitive database fields (GoogleCalendarCredential, etc.)
FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY', '')
if not FIELD_ENCRYPTION_KEY:
    if DEBUG:
        import warnings
        warnings.warn("FIELD_ENCRYPTION_KEY not set. Using insecure dev key. DO NOT USE IN PRODUCTION!")
        # Use a valid Fernet key for development (NOT secure for production)
        FIELD_ENCRYPTION_KEY = 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg='
    else:
        import sys
        print("ERROR: FIELD_ENCRYPTION_KEY is required in production for encrypted database fields")
        print("Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        sys.exit(1)

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,aresai.space,www.aresai.space').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'encrypted_model_fields',  # SECURITY: Field encryption for sensitive data
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ares_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ares_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'America/New_York')  # Default to Eastern Time
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.auth.Auth0Authentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Allow auth/config endpoint to be accessed without authentication
# This is handled in the view itself with @csrf_exempt

CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",  # Keep for dev mode
    "http://127.0.0.1:3000",  # Keep for dev mode
    "https://aresai.space",
    "https://www.aresai.space",
]

CORS_ALLOW_CREDENTIALS = True

# Trust proxy headers (required when behind nginx/load balancer)
# This allows Django to detect HTTPS when behind a reverse proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_TLS = True

# Security settings for HTTPS (when not in DEBUG mode)
if not DEBUG:
    SECURE_SSL_REDIRECT = False  # Let nginx handle redirects
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN', '')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID', '')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET', '')
AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE', '')

# Auth0 Management API (M2M) Configuration
# These are separate credentials for a Machine-to-Machine application
# Create an M2M app in Auth0 Dashboard > Applications > Create Application > Machine to Machine
# Grant it permissions: read:users, read:roles, read:role_members
AUTH0_M2M_CLIENT_ID = os.getenv('AUTH0_M2M_CLIENT_ID', '')
AUTH0_M2M_CLIENT_SECRET = os.getenv('AUTH0_M2M_CLIENT_SECRET', '')

# GEMMA AI API Configuration
GEMMA_AI_API_URL = os.getenv('GEMMA_AI_API_URL', 'http://localhost:60006')

# Stable Diffusion API Configuration
SD_API_URL = os.getenv('VITE_SD_API_URL', 'http://host.docker.internal:7860')

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')

# Telegram integration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

# Logging (also written to /app/logs/backend.log inside docker)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
BACKEND_LOG_FILE = LOG_DIR / "backend.log"

from django.utils import timezone as django_timezone

class TimezoneFormatter(logging.Formatter):
    """Custom formatter that uses Django's TIME_ZONE setting"""
    def formatTime(self, record, datefmt=None):
        # Convert the record's timestamp to Django's timezone
        dt = datetime.fromtimestamp(record.created, tz=django_timezone.get_current_timezone())
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "()": TimezoneFormatter,
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %Z",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": str(BACKEND_LOG_FILE),
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        }
    },
}

