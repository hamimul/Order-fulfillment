"""
Django settings auto-loader for order_fulfillment project.

This file automatically loads the appropriate settings based on the environment.
The settings are organized in a package structure for better maintainability.

Environment Detection Priority:
1. If running tests ('test' in sys.argv or 'pytest' detected) -> testing settings
2. DJANGO_ENVIRONMENT environment variable -> production/development
3. DEBUG environment variable -> production if False, development if True
4. Default -> development settings

Available settings modules:
- order_fulfillment.settings.development (default)
- order_fulfillment.settings.production
- order_fulfillment.settings.testing
"""

import os
import sys
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

def get_environment():
    """
    Determine which environment settings to load based on various indicators.
    """
    # 1. Check if running tests
    if 'test' in sys.argv or 'pytest' in sys.modules or 'unittest' in sys.modules:
        return 'testing'

    # 2. Check explicit environment variable
    django_env = os.getenv('DJANGO_ENVIRONMENT', '').lower()
    if django_env in ['production', 'prod']:
        return 'production'
    elif django_env in ['development', 'dev']:
        return 'development'
    elif django_env == 'testing':
        return 'testing'

    # 3. Check DEBUG environment variable
    debug_env = os.getenv('DEBUG', '').lower()
    if debug_env in ['false', '0', 'no']:
        return 'production'
    elif debug_env in ['true', '1', 'yes']:
        return 'development'

    # 4. Default to development
    return 'development'

# Determine environment
ENVIRONMENT = get_environment()

# Import appropriate settings
try:
    if ENVIRONMENT == 'testing':
        from .settings.testing import *
        settings_module = 'testing'
    elif ENVIRONMENT == 'production':
        from .settings.production import *
        settings_module = 'production'
    else:  # development
        from .settings.development import *
        settings_module = 'development'

except ImportError as e:
    # Fallback to base settings if specific environment settings fail
    print(f"Warning: Could not import {ENVIRONMENT} settings: {e}")
    print("Falling back to base settings...")
    from .settings.base import *
    settings_module = 'base'

# Debug output (only if explicitly requested)
if os.getenv('DJANGO_SETTINGS_DEBUG', 'False').lower() == 'true':
    print(f"Django Environment: {ENVIRONMENT}")
    print(f"Settings Module: order_fulfillment.settings.{settings_module}")
    print(f"DEBUG: {globals().get('DEBUG', 'Not Set')}")
    print(f"ALLOWED_HOSTS: {globals().get('ALLOWED_HOSTS', 'Not Set')}")

    # Show database info (without password)
    db_config = globals().get('DATABASES', {}).get('default', {})
    if db_config:
        print(f"Database: {db_config.get('ENGINE', 'Unknown')} at {db_config.get('HOST', 'localhost')}:{db_config.get('PORT', 'default')}")

# Validation for critical settings in production
if ENVIRONMENT == 'production':
    critical_settings = ['SECRET_KEY', 'ALLOWED_HOSTS']
    missing_settings = []

    for setting in critical_settings:
        value = globals().get(setting)
        if not value or (isinstance(value, (list, tuple)) and not any(value)):
            missing_settings.append(setting)

    if missing_settings:
        raise ValueError(
            f"Critical settings missing for production: {', '.join(missing_settings)}. "
            f"Please check your environment variables."
        )