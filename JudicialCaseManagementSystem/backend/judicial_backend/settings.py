"""
Django settings for judicial_backend project.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG_RAW = str(config('DEBUG', default='True')).strip().lower()
DEBUG = DEBUG_RAW in ('1', 'true', 'yes', 'on')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    # Django defaults
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_extensions',
    
    # Local apps
    'apps.authentication.apps.AuthenticationConfig',
    'apps.cases.apps.CasesConfig',
    'apps.courts.apps.CourtsConfig',
    'apps.documents.apps.DocumentsConfig',
    'apps.hearings.apps.HearingsConfig',
    'apps.orders.apps.OrdersConfig',
    'apps.tasks.apps.TasksConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.ai_assistant.apps.AiAssistantConfig',
    'apps.audit.apps.AuditConfig',
    'apps.analytics.apps.AnalyticsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # JCM enterprise
    'apps.common.middleware.RequestIDMiddleware',
    'apps.common.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'judicial_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'judicial_backend.wsgi.application'

# Database
DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')
DB_NAME = config('DB_NAME', default=BASE_DIR / 'db.sqlite3')
if DB_ENGINE == 'django.db.backends.sqlite3':
    db_name_str = str(DB_NAME)
    if os.path.isabs(db_name_str) or Path(db_name_str).suffix in ('.sqlite', '.sqlite3'):
        DB_NAME = DB_NAME
    else:
        DB_NAME = BASE_DIR / 'db.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authentication.User'

# REST Framework Configuration
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.common.exceptions.jcm_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', 
    default='http://localhost:3000,http://127.0.0.1:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

# Security Settings for Production
if not DEBUG:
    LOCAL_HOSTS = {'localhost', '127.0.0.1'}
    SECURE_SSL_REDIRECT = not all(host in LOCAL_HOSTS for host in ALLOWED_HOSTS if host)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
    }

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'judicial.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# File Upload Settings
MAX_UPLOAD_SIZE = 10485760  # 10MB
ALLOWED_FILE_TYPES = ['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt']

# AI Settings
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
USE_LOCAL_LLM = config('USE_LOCAL_LLM', default=False, cast=bool)
OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://localhost:11434')

# Gemini Settings
# Get a free API key at https://aistudio.google.com/apikey
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.5-flash')

# Vector Database
VECTOR_DB_TYPE = config('VECTOR_DB_TYPE', default='faiss')  # 'faiss' or 'pinecone'
PINECONE_API_KEY = config('PINECONE_API_KEY', default='')
PINECONE_ENVIRONMENT = config('PINECONE_ENVIRONMENT', default='us-west-2')
PINECONE_INDEX = config('PINECONE_INDEX', default='judicial-cases')

# Admin access controls
ADMIN_SIGNUP_CODE = config('ADMIN_SIGNUP_CODE', default='JCM-ADMIN-SIGNUP-2026')
ADMIN_LOGIN_CODE = config('ADMIN_LOGIN_CODE', default='JCM-ADMIN-LOGIN-2026')

# ---------------------------------------------------------------------------
# JCM Enterprise additions
# ---------------------------------------------------------------------------

# PostgreSQL + pgvector
# pgvector extension is created via the first migration (RunSQL).
VECTOR_EMBEDDING_DIM = int(config('VECTOR_EMBEDDING_DIM', default=768))
EMBEDDING_MODEL = config('EMBEDDING_MODEL', default='gemini-embedding-001')

# Celery / Redis
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_BEAT_SCHEDULE = {}
# Run tasks synchronously when no worker is present (dev convenience).
# Set CELERY_TASK_ALWAYS_EAGER=False in production with a real worker.
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=True, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Object storage abstraction
# storage backend: 'local' (default) or 's3'
STORAGE_BACKEND = config('STORAGE_BACKEND', default='local')
S3_ENDPOINT = config('S3_ENDPOINT', default='')
S3_BUCKET = config('S3_BUCKET', default='')
S3_ACCESS_KEY = config('S3_ACCESS_KEY', default='')
S3_SECRET_KEY = config('S3_SECRET_KEY', default='')
S3_REGION = config('S3_REGION', default='us-east-1')
S3_PUBLIC_BASE_URL = config('S3_PUBLIC_BASE_URL', default='')
# Signed URL lifetime in seconds
SIGNED_URL_TTL = int(config('SIGNED_URL_TTL', default=300))

# AI provider abstraction
# ai_provider: 'gemini' (default) | 'openai' | 'anthropic' | 'local'
AI_PROVIDER = config('AI_PROVIDER', default='gemini')
AI_CHAT_MODEL = config('AI_CHAT_MODEL', default=GEMINI_MODEL)
AI_TEMPERATURE = float(config('AI_TEMPERATURE', default=0.2))
AI_MAX_OUTPUT_TOKENS = int(config('AI_MAX_OUTPUT_TOKENS', default=2048))
AI_EMBEDDING_MODEL = config('AI_EMBEDDING_MODEL', default=EMBEDDING_MODEL)

# Request ID middleware / logging
REQUEST_ID_HEADER = 'HTTP_X_REQUEST_ID'
