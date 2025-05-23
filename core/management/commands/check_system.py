from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import redis
import psutil
import requests
from orders.models import Order
from products.models import Product
from inventory.models import InventoryItem


class Command(BaseCommand):
    help = 'Perform comprehensive system health check'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information'
        )
        parser.add_argument(
            '--check-api',
            action='store_true',
            help='Check API endpoints'
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.check_api = options['check_api']

        self.stdout.write('=' * 60)
        self.stdout.write('SYSTEM HEALTH CHECK')
        self.stdout.write('=' * 60)

        # Check database
        self.check_database()

        # Check Redis
        self.check_redis()

        # Check Celery
        self.check_celery()

        # Check system resources
        self.check_system_resources()

        # Check application data
        self.check_application_data()

        # Check API endpoints if requested
        if self.check_api:
            self.check_api_endpoints()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('System health check completed!'))

    def check_database(self):
        self.stdout.write('\n📊 DATABASE CHECK')
        self.stdout.write('-' * 20)

        try:
            with connection.cursor() as cursor:
                # Basic connectivity
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]

                # Check migrations
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                migration_count = cursor.fetchone()[0]

                # Check table sizes
                cursor.execute("""
                               SELECT schemaname,
                                      tablename,
                                      pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
                               FROM pg_tables
                               WHERE schemaname = 'public'
                               ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                                   LIMIT 5
                               """)
                tables = cursor.fetchall()

            self.stdout.write(self.style.SUCCESS('✓ Database: HEALTHY'))

            if self.verbose:
                self.stdout.write(f'  Version: {version}')
                self.stdout.write(f'  Migrations applied: {migration_count}')
                self.stdout.write('  Largest tables:')
                for schema, table, size in tables:
                    self.stdout.write(f'    {table}: {size}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database: UNHEALTHY - {str(e)}'))

    def check_redis(self):
        self.stdout.write('\n🔴 REDIS CHECK')
        self.stdout.write('-' * 15)

        try:
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            info = r.info()

            self.stdout.write(self.style.SUCCESS('✓ Redis: HEALTHY'))

            if self.verbose:
                self.stdout.write(f'  Version: {info.get("redis_version", "unknown")}')
                self.stdout.write(f'  Connected clients: {info.get("connected_clients", 0)}')
                self.stdout.write(f'  Used memory: {info.get("used_memory_human", "unknown")}')
                self.stdout.write(f'  Total commands processed: {info.get("total_commands_processed", 0)}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Redis: UNHEALTHY - {str(e)}'))

    def check_celery(self):
        self.stdout.write('\n🐝 CELERY CHECK')
        self.stdout.write('-' * 16)

        try:
            from order_fulfillment.celery import app
            inspect = app.control.inspect()

            # Check active workers
            active = inspect.active()
            stats = inspect.stats()

            if active:
                worker_count = len(active.keys())
                self.stdout.write(self.style.SUCCESS(f'✓ Celery: HEALTHY ({worker_count} workers)'))

                if self.verbose:
                    for worker, tasks in active.items():
                        self.stdout.write(f'  Worker: {worker}')
                        self.stdout.write(f'    Active tasks: {len(tasks)}')
                        if worker in stats:
                            worker_stats = stats[worker]
                            self.stdout.write(f'    Total tasks: {worker_stats.get("total", 0)}')
                            self.stdout.write(f'    Pool: {worker_stats.get("pool", {})}')
            else:
                self.stdout.write(self.style.WARNING('⚠ Celery: NO WORKERS'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Celery: UNHEALTHY - {str(e)}'))

    def check_system_resources(self):
        self.stdout.write('\n💻 SYSTEM RESOURCES')
        self.stdout.write('-' * 21)

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory
            memory = psutil.virtual_memory()

            # Disk
            disk = psutil.disk_usage('/')

            # Load average (Unix only)
            try:
                load_avg = psutil.getloadavg()
                load_str = f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
            except:
                load_str = "N/A (Windows)"

            self.stdout.write(self.style.SUCCESS('✓ System Resources: MONITORED'))

            if self.verbose:
                self.stdout.write(f'  CPU Usage: {cpu_percent}% ({cpu_count} cores)')
                self.stdout.write(
                    f'  Memory Usage: {memory.percent}% ({self.bytes_to_human(memory.used)}/{self.bytes_to_human(memory.total)})')
                self.stdout.write(
                    f'  Disk Usage: {disk.percent}% ({self.bytes_to_human(disk.used)}/{self.bytes_to_human(disk.total)})')
                self.stdout.write(f'  Load Average: {load_str}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ System Resources: ERROR - {str(e)}'))

    def check_application_data(self):
        self.stdout.write('\n📦 APPLICATION DATA')
        self.stdout.write('-' * 21)

        try:
            # Count records
            product_count = Product.objects.count()
            order_count = Order.objects.count()
            inventory_count = InventoryItem.objects.count()

            # Check for issues
            pending_orders = Order.objects.filter(status='pending').count()
            failed_orders = Order.objects.filter(status='failed').count()
            low_stock_items = InventoryItem.objects.filter(
                quantity__lte=10  # Simple low stock check
            ).count()

            self.stdout.write(self.style.SUCCESS('✓ Application Data: ACCESSIBLE'))

            if self.verbose:
                self.stdout.write(f'  Products: {product_count}')
                self.stdout.write(f'  Orders: {order_count}')
                self.stdout.write(f'  Inventory Items: {inventory_count}')
                self.stdout.write(f'  Pending Orders: {pending_orders}')
                self.stdout.write(f'  Failed Orders: {failed_orders}')
                self.stdout.write(f'  Low Stock Items: {low_stock_items}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Application Data: ERROR - {str(e)}'))

    def check_api_endpoints(self):
        self.stdout.write('\n🌐 API ENDPOINTS')
        self.stdout.write('-' * 17)

        base_url = 'http://localhost:8000'
        endpoints = [
            '/health/',
            '/api/v1/products/',
            '/api/v1/orders/',
            '/api/v1/inventory/',
            '/swagger.json'
        ]

        for endpoint in endpoints:
            try:
                response = requests.get(f'{base_url}{endpoint}', timeout=5)
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {endpoint} - OK'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {endpoint} - {response.status_code}'))
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'  ✗ {endpoint} - {str(e)}'))

    def bytes_to_human(self, bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"