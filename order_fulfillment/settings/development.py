"""
Development settings for order_fulfillment project.
These settings are for local development only.
"""

from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-development-key-change-in-production')

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']

# Development-specific apps
INSTALLED_APPS += [
    'django_extensions',  # Useful development tools
]

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_ALL_ORIGINS = True  # Only for development!
CORS_ALLOW_CREDENTIALS = True

# Database configuration for development
DATABASES['default'].update({
    'OPTIONS': {
        'options': '-c default_transaction_isolation=read_committed'  # Less strict for dev
    },
    'CONN_MAX_AGE': 60,  # Shorter for development
})

# Cache configuration for development
CACHES['default'].update({
    'OPTIONS': {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        'CONNECTION_POOL_KWARGS': {
            'max_connections': 10,  # Lower for development
            'retry_on_timeout': True,
        },
    },
    'TIMEOUT': 300,
})

# Disable rate limiting in development
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        'user': '10000/hour'
    }
})

# Development logging
LOGGING.update({
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django_dev.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Set to DEBUG to see SQL queries
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'products': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
})

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development-specific security settings (relaxed)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Celery settings for development
CELERY_TASK_ALWAYS_EAGER = False  # Set to True to run tasks synchronously
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = True

# Development-specific settings
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Django Debug Toolbar (optional - requires installation)
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG and request.META.get('REMOTE_ADDR') in INTERNAL_IPS,
        'HIDE_DJANGO_SQL': False,
        'SHOW_TEMPLATE_CONTEXT': True,
    }

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]
except ImportError:
    pass

# Django Extensions settings
if 'django_extensions' in INSTALLED_APPS:
    # Enable additional management commands
    SHELL_PLUS_PRINT_SQL = True
    SHELL_PLUS_DONT_LOAD = []

# File upload settings for development
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB for development
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB for development

# Development-specific cache settings
SESSION_COOKIE_AGE = 60 * 60 * 24  # 1 day for development
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# API settings for development
SWAGGER_SETTINGS = {
    'DEEP_LINKING': True,
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_WITH_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,
    'DEFAULT_INFO': 'order_fulfillment.urls.api_info',
    'USE_SESSION_AUTH': True,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get',
        'post',
        'put',
        'delete',
        'patch'
    ],
}

# Disable some security features for easier development
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

print("🚀 Development settings loaded - Debug mode enabled")
print(f"📍 Base directory: {BASE_DIR}")
print(f"🗃️  Database: {DATABASES['default']['NAME']} at {DATABASES['default']['HOST']}")
print(f"🔴 Redis: {CACHES['default']['LOCATION']}")
print(f"📝 Logs directory: {BASE_DIR / 'logs'}")