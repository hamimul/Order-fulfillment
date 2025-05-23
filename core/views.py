from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
import redis
import logging
import psutil
import os

logger = logging.getLogger(__name__)


@api_view(['GET'])
def health_check(request):
    """Comprehensive health check endpoint for monitoring"""
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
        'environment': 'development' if settings.DEBUG else 'production',
        'checks': {},
        'system': {}
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            migration_count = cursor.fetchone()[0]
        health_status['checks']['database'] = {
            'status': 'healthy',
            'migrations_applied': migration_count
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # Redis check
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        info = r.info()
        health_status['checks']['redis'] = {
            'status': 'healthy',
            'connected_clients': info.get('connected_clients', 0),
            'used_memory_human': info.get('used_memory_human', 'unknown')
        }
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # Celery worker check
    try:
        from order_fulfillment.celery import app
        inspect = app.control.inspect()
        active_nodes = inspect.active()
        stats = inspect.stats()

        if active_nodes:
            worker_count = len(active_nodes.keys())
            health_status['checks']['celery_workers'] = {
                'status': 'healthy',
                'active_workers': worker_count,
                'worker_stats': stats
            }
        else:
            health_status['checks']['celery_workers'] = {
                'status': 'no_workers',
                'message': 'No active Celery workers found'
            }
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['celery_workers'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # System resource check
    try:
        health_status['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
        }
    except Exception as e:
        logger.warning(f"Could not get system stats: {e}")

    # Application-specific checks
    try:
        from products.models import Product
        from orders.models import Order
        from inventory.models import InventoryItem

        health_status['checks']['application'] = {
            'status': 'healthy',
            'total_products': Product.objects.count(),
            'total_orders': Order.objects.count(),
            'total_inventory_items': InventoryItem.objects.count(),
            'pending_orders': Order.objects.filter(status='pending').count()
        }
    except Exception as e:
        health_status['checks']['application'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'unhealthy'

    # Set appropriate HTTP status code
    status_code = 200
    if health_status['status'] == 'unhealthy':
        status_code = 503
    elif health_status['status'] == 'degraded':
        status_code = 200  # Still accepting requests

    return Response(health_status, status=status_code)


@api_view(['GET'])
def system_metrics(request):
    """System metrics endpoint for monitoring"""
    try:
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_avg': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'processes': len(psutil.pids()),
            'boot_time': psutil.boot_time()
        }

        return Response(metrics)
    except Exception as e:
        return Response(
            {'error': f'Could not get system metrics: {str(e)}'},
            status=500
        )