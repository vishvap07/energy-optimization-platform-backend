"""
Django settings for energy_platform project.
"""
import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

# ---------------------------------------------------------------------------
# .env Validation
# ---------------------------------------------------------------------------
if os.environ.get('DEBUG', 'True') == 'False':
    if not os.environ.get('SECRET_KEY'):
        raise ImproperlyConfigured("SECRET_KEY must be set in production (DEBUG=False)")
    if os.environ.get('DB_ENGINE') == 'django.db.backends.postgresql' and not os.environ.get('DB_PASSWORD'):
        raise ImproperlyConfigured("DB_PASSWORD must be set when using PostgreSQL in production")

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ML package path — add the project root so `ml_models` is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ML_MODEL_PATH = str(PROJECT_ROOT / 'ml_models' / 'saved_models' / 'lstm_model.h5')
ML_SCALER_PATH = str(PROJECT_ROOT / 'ml_models' / 'saved_models' / 'scaler.pkl')
ML_CSV_PATH = str(PROJECT_ROOT / 'demo_energy_data.csv')

# Hugging Face Space Integration
HF_SPACE_ID = os.environ.get('HF_SPACE_ID', 'Vishva1574/EnergyForecasting')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-energy-platform-secret-key-2024')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'axes',
    # Local apps
    'apps.authentication',
    'apps.analytics',
    'apps.forecasting',
    'apps.optimization',
    'apps.tickets',
    'apps.chatbot',
    'apps.monitoring',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'energy_platform.urls'

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

WSGI_APPLICATION = 'energy_platform.wsgi.application'

import dj_database_url

_db_url = os.environ.get('DATABASE_URL')
_db_engine = os.environ.get('DB_ENGINE', '')

if _db_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif _db_engine.startswith(('postgres://', 'postgresql://', 'mysql://', 'sqlite://')):
    # Provide a fallback just in case the connection string was passed via DB_ENGINE
    DATABASES = {
        'default': dj_database_url.parse(
            _db_engine,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _db_engine or 'django.db.backends.sqlite3',
            'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', ''),
            'PORT': os.environ.get('DB_PORT', ''),
        }
    }

AUTH_USER_MODEL = 'authentication.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'energy_platform.validators.ComplexityValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True  # Can be tightened later with CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Logging — console only for Render compatibility; file logging is optional locally
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ---------------------------------------------------------------------------
# Security Headers & Hardening
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'same-origin'

# Axes Configuration (Account Lockout)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # Hour
AXES_LOCKOUT_TEMPLATE = None # Use default or custom
AXES_RESET_ON_SUCCESS = True

# Ratelimit Configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
