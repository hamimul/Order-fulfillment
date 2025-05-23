"""
Testing settings for order_fulfillment project.
These settings are optimized for running tests with speed and isolation.
"""

from .base import *
import os
import tempfile

# Test-specific settings
DEBUG = False
SECRET_KEY = 'django-insecure-test-key-only-for-testing-' + 'x' * 50
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Use in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'OPTIONS': {
            'timeout': 20,
        },
        'TEST': {
            'NAME': ':memory:',
        }
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Use dummy cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use locmem email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable password validators for tests
AUTH_PASSWORD_VALIDATORS = []

# Test-specific logging (minimal to reduce noise)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'CRITICAL',  # Only show critical errors during tests
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'orders': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'products': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'celery': {
            'handlers': ['null'],
            'level': 'CRITICAL',
            'propagate': False,
        },
    },
}

# Disable throttling for tests
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
    'DEFAULT_PAGINATION_CLASS': None,  # Disable pagination for easier testing
})

# Celery settings for testing (synchronous execution)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Disable simple history for faster tests
SIMPLE_HISTORY_ENABLED = False

# Static files for testing
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files for testing (use temporary directory)
MEDIA_ROOT = tempfile.mkdtemp()

# Security settings (disabled for testing)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

# Performance optimizations for tests
CONN_MAX_AGE = 0

# Test database creation settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_NON_SERIALIZED_APPS = []

# Disable debug toolbar in tests
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

# Remove debug toolbar middleware if present
MIDDLEWARE = [mw for mw in MIDDLEWARE if 'debug_toolbar' not in mw]

# Remove django_extensions from test apps
if 'django_extensions' in INSTALLED_APPS:
    INSTALLED_APPS.remove('django_extensions')

# Session settings for tests
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60  # 1 hour for tests

# File upload settings (smaller limits for tests)
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB

# CORS settings for tests
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Disable whitenoise for tests
MIDDLEWARE = [mw for mw in MIDDLEWARE if 'whitenoise' not in mw]

# Test-specific Django settings
USE_TZ = True
TIME_ZONE = 'UTC'

# Override any environment-specific settings that might interfere with tests
os.environ.pop('DJANGO_SETTINGS_DEBUG', None)

# Ensure test isolation
import django
from django.test.utils import get_runner

class FastTestRunner(get_runner(django.conf.settings)):
    """Custom test runner optimized for speed"""
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # Disable logging below CRITICAL level during tests
        import logging
        logging.disable(logging.CRITICAL)

    def teardown_test_environment(self, **kwargs):
        super().teardown_test_environment(**kwargs)
        # Re-enable logging
        import logging
        logging.disable(logging.NOTSET)

TEST_RUNNER = 'order_fulfillment.settings.testing.FastTestRunner'

# Additional test settings
TESTING = True

# Print confirmation that test settings are loaded
import sys
if 'test' in sys.argv:
    print("🧪 Test settings loaded - optimized for speed and isolation")
    print(f"📊 Database: In-memory SQLite")
    print(f"📦 Cache: Dummy backend")
    print(f"📧 Email: Local memory backend")
    print(f"🔄 Celery: Synchronous execution")
    print(f"📝 Logging: Disabled for performance")