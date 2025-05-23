"""
Production settings for order_fulfillment project.
These settings are optimized for production deployment with security and performance in mind.
"""

from .base import *
import os
import logging

# SECURITY SETTINGS
DEBUG = False

# SECRET_KEY must be set in environment variables
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set for production")

# ALLOWED_HOSTS must be properly configured
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS environment variable must be set for production")

# Clean up ALLOWED_HOSTS
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

# Security middleware
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# CORS settings for production
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
else:
    CORS_ALLOWED_ORIGINS = []

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# Database configuration for production
DATABASES['default'].update({
    'CONN_MAX_AGE': 600,
    'OPTIONS': {
        'sslmode': os.getenv('DB_SSL_MODE', 'prefer'),
        'options': '-c default_transaction_isolation=serializable'
    }
})

# Add read replica if configured
if os.getenv('DB_READ_HOST'):
    DATABASES['read'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'order_fulfillment'),
        'USER': os.getenv('DB_READ_USER', os.getenv('DB_USER', 'postgres')),
        'PASSWORD': os.getenv('DB_READ_PASSWORD', os.getenv('DB_PASSWORD')),
        'HOST': os.getenv('DB_READ_HOST'),
        'PORT': os.getenv('DB_READ_PORT', '5432'),
        'OPTIONS': {
            'sslmode': os.getenv('DB_SSL_MODE', 'prefer'),
            'options': '-c default_transaction_isolation=read_committed'
        },
        'CONN_MAX_AGE': 600,
    }

# Static files configuration with WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False
WHITENOISE_MAX_AGE = 31536000  # 1 year

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 year
# SECURE_REDIRECT_EXEMPT = [r'^health/, r'^health/metrics/]  # Allow health checks over HTTP
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# Additional security headers
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', str(60 * 60 * 24 * 7)))  # 1 week

# CSRF security
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host and host != 'localhost']

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '60'))

# Production cache configuration
CACHES['default'].update({
    'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
    'OPTIONS': {
        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        'CONNECTION_POOL_KWARGS': {
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
            'retry_on_timeout': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
        },
        'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        'IGNORE_EXCEPTIONS': True,
    },
    'KEY_PREFIX': 'order_fulfillment_prod',
    'VERSION': 1,
    'TIMEOUT': int(os.getenv('CACHE_TIMEOUT', '300')),  # 5 minutes
})

# REST Framework production settings
REST_FRAMEWORK.update({
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('API_ANON_RATE_LIMIT', '100/hour'),
        'user': os.getenv('API_USER_RATE_LIMIT', '1000/hour'),
        'burst': os.getenv('API_BURST_RATE_LIMIT', '60/min'),
    }
})

# Production logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "process": %(process)d, "thread": %(thread)d, "message": "%(message)s"}',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'json',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django_error.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django_security.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'products': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Celery production configuration
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_RESULT_BACKEND_DB_RETRY = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '1000'))
CELERY_WORKER_CONCURRENCY = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))

# File upload security
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_SIZE', str(50 * 1024 * 1024)))  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_SIZE', str(50 * 1024 * 1024)))  # 50MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv('DATA_UPLOAD_MAX_FIELDS', '1000'))

# Admin security
ADMIN_URL = os.getenv('ADMIN_URL', 'admin/')

# Performance optimizations
CONN_MAX_AGE = 600

# Monitoring and health checks
HEALTH_CHECK_URL = 'health/'

# Error reporting with Sentry (optional)
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(
                    transaction_style='url',
                    middleware_spans=True,
                    signals_spans=True,
                    cache_spans=True,
                ),
                CeleryIntegration(monitor_beat_tasks=True),
                RedisIntegration(),
                sentry_logging,
            ],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
            release=os.getenv('APP_VERSION', 'unknown'),
        )
        print("✅ Sentry error reporting configured")
    except ImportError:
        print("⚠️ Sentry SDK not installed, skipping error reporting setup")

# Content Security Policy (if django-csp is installed)
try:
    import csp
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'")
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
    CSP_IMG_SRC = ("'self'", "data:")
    CSP_FONT_SRC = ("'self'",)
    CSP_CONNECT_SRC = ("'self'",)
    CSP_FRAME_ANCESTORS = ("'none'",)
    CSP_FRAME_SRC = ("'none'",)
    CSP_OBJECT_SRC = ("'none'",)
    CSP_BASE_URI = ("'self'",)
    CSP_FORM_ACTION = ("'self'",)
    print("✅ Content Security Policy configured")
except ImportError:
    pass

# API Documentation (disabled in production by default)
if os.getenv('ENABLE_API_DOCS', 'False').lower() == 'true':
    SWAGGER_SETTINGS = {
        'DEEP_LINKING': True,
        'PERSIST_AUTH': True,
        'REFETCH_SCHEMA_WITH_AUTH': True,
        'REFETCH_SCHEMA_ON_LOGOUT': True,
        'SECURITY_DEFINITIONS': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header'
            }
        },
        'USE_SESSION_AUTH': False,
    }
else:
    # Disable API documentation in production
    SWAGGER_SETTINGS = {'ENABLED': False}

print("🚀 Production settings loaded")
print(f"🔒 Security: SSL={SECURE_SSL_REDIRECT}, HSTS={SECURE_HSTS_SECONDS}s")
print(f"🗃️  Database: {DATABASES['default']['NAME']} at {DATABASES['default']['HOST']}")
print(f"🔴 Cache: {CACHES['default']['LOCATION']}")
print(f"📧 Email: {EMAIL_HOST}:{EMAIL_PORT} (TLS={EMAIL_USE_TLS})")
print(f"📊 Monitoring: Sentry={'enabled' if SENTRY_DSN else 'disabled'}")
print(f"📝 Logging: {len(LOGGING['handlers'])} handlers configured")