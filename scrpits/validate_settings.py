#!/usr/bin/env python
"""
Settings validation script for Order Fulfillment System.
This script validates that all settings configurations are working correctly.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def test_environment_settings():
    """Test settings loading for different environments"""
    environments = ['development', 'production', 'testing']
    results = {}

    for env in environments:
        print(f"\n{'=' * 50}")
        print(f"Testing {env.upper()} settings")
        print(f"{'=' * 50}")

        try:
            # Set environment
            os.environ['DJANGO_ENVIRONMENT'] = env

            # Clear Django settings if already loaded
            if hasattr(django.conf.settings, '_wrapped'):
                django.conf.settings._wrapped = None

            # Import settings
            os.environ['DJANGO_SETTINGS_MODULE'] = 'order_fulfillment.settings'
            django.setup()

            from django.conf import settings

            # Validate critical settings
            validation_results = validate_settings(settings, env)
            results[env] = validation_results

            if validation_results['valid']:
                print(f"✅ {env.capitalize()} settings: VALID")
            else:
                print(f"❌ {env.capitalize()} settings: INVALID")
                for error in validation_results['errors']:
                    print(f"   - {error}")

            # Print key settings
            print(f"   DEBUG: {settings.DEBUG}")
            print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
            print(f"   DATABASE: {settings.DATABASES['default']['ENGINE']}")
            print(f"   CACHE: {settings.CACHES['default']['BACKEND']}")
            print(f"   CELERY_BROKER: {settings.CELERY_BROKER_URL}")

        except Exception as e:
            print(f"❌ {env.capitalize()} settings: ERROR - {str(e)}")
            results[env] = {'valid': False, 'errors': [str(e)]}

    return results


def validate_settings(settings, environment):
    """Validate specific settings for an environment"""
    errors = []

    # Common validations
    if not hasattr(settings, 'SECRET_KEY'):
        errors.append("SECRET_KEY is missing")
    elif environment == 'production' and 'django-insecure' in settings.SECRET_KEY:
        errors.append("Production SECRET_KEY should not contain 'django-insecure'")

    if not hasattr(settings, 'DATABASES'):
        errors.append("DATABASES configuration is missing")
    elif not settings.DATABASES.get('default'):
        errors.append("Default database configuration is missing")

    if not hasattr(settings, 'INSTALLED_APPS'):
        errors.append("INSTALLED_APPS is missing")
    else:
        required_apps = ['django.contrib.admin', 'rest_framework', 'orders', 'products', 'inventory']
        missing_apps = [app for app in required_apps if app not in settings.INSTALLED_APPS]
        if missing_apps:
            errors.append(f"Missing required apps: {missing_apps}")

    # Environment-specific validations
    if environment == 'development':
        if not settings.DEBUG:
            errors.append("DEBUG should be True in development")

    elif environment == 'production':
        if settings.DEBUG:
            errors.append("DEBUG should be False in production")

        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ['']:
            errors.append("ALLOWED_HOSTS must be configured for production")

    elif environment == 'testing':
        if settings.DEBUG:
            errors.append("DEBUG should be False in testing")

        if 'sqlite3' not in settings.DATABASES['default']['ENGINE']:
            errors.append("Testing should use SQLite for speed")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def test_imports():
    """Test that all Django components can be imported"""
    print(f"\n{'=' * 50}")
    print("Testing Django imports")
    print(f"{'=' * 50}")

    try:
        # Test basic Django imports
        from django.conf import settings
        from django.core.management import execute_from_command_line
        from django.urls import reverse
        print("✅ Core Django imports: OK")

        # Test DRF imports
        from rest_framework import serializers, viewsets
        from rest_framework.response import Response
        print("✅ Django REST Framework imports: OK")

        # Test Celery imports
        from celery import Celery
        print("✅ Celery imports: OK")

        # Test app imports
        from products.models import Product
        from orders.models import Order
        from inventory.models import InventoryItem
        print("✅ App model imports: OK")

        # Test signal imports
        from orders.signals import order_created_or_updated
        from inventory.signals import create_inventory_item
        print("✅ Signal imports: OK")

        return True

    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False


def main():
    """Main validation function"""
    print("🔍 Order Fulfillment System - Settings Validation")
    print("=" * 60)

    # Test imports first
    imports_ok = test_imports()

    # Test environment settings
    results = test_environment_settings()

    # Summary
    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 60}")

    print(f"Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")

    for env, result in results.items():
        status = '✅ PASS' if result['valid'] else '❌ FAIL'
        print(f"{env.capitalize()} Settings: {status}")

    all_valid = imports_ok and all(r['valid'] for r in results.values())

    if all_valid:
        print(f"\n🎉 All validations passed!")
        return 0
    else:
        print(f"\n⚠️  Some validations failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())