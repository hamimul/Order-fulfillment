from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
import time
import psutil
import json
import os
from datetime import timedelta


class Command(BaseCommand):
    help = 'Monitor system performance over time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='Monitoring duration in seconds (default: 60)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Sampling interval in seconds (default: 5)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for performance data (JSON format)'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress console output'
        )

    def handle(self, *args, **options):
        duration = options['duration']
        interval = options['interval']
        output_file = options['output']
        quiet = options['quiet']

        if not quiet:
            self.stdout.write('=' * 60)
            self.stdout.write('PERFORMANCE MONITORING')
            self.stdout.write('=' * 60)
            self.stdout.write(f'Duration: {duration} seconds')
            self.stdout.write(f'Interval: {interval} seconds')
            self.stdout.write(f'Samples: {duration // interval}')
            if output_file:
                self.stdout.write(f'Output: {output_file}')
            self.stdout.write('')

        # Collect performance data
        performance_data = []
        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                sample = self.collect_sample()
                performance_data.append(sample)

                if not quiet:
                    self.display_sample(sample)

                time.sleep(interval)

        except KeyboardInterrupt:
            if not quiet:
                self.stdout.write('\nMonitoring interrupted by user')

        # Generate summary
        if performance_data:
            summary = self.generate_summary(performance_data)

            if not quiet:
                self.display_summary(summary)

            # Save to file if requested
            if output_file:
                self.save_results(performance_data, summary, output_file)
                if not quiet:
                    self.stdout.write(f'\nResults saved to: {output_file}')

    def collect_sample(self):
        """Collect a single performance sample"""
        timestamp = timezone.now()

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Database metrics
        db_metrics = self.get_database_metrics()

        # Application metrics
        app_metrics = self.get_application_metrics()

        return {
            'timestamp': timestamp.isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used / (1024 * 1024),
            'disk_percent': disk.percent,
            'database': db_metrics,
            'application': app_metrics
        }

    def get_database_metrics(self):
        """Get database performance metrics"""
        try:
            with connection.cursor() as cursor:
                # Active connections
                cursor.execute("""
                               SELECT count(*)
                               FROM pg_stat_activity
                               WHERE state = 'active'
                               """)
                active_connections = cursor.fetchone()[0]

                # Database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                db_size = cursor.fetchone()[0]

                # Query performance
                start_time = time.time()
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                query_time = time.time() - start_time

                return {
                    'active_connections': active_connections,
                    'database_size': db_size,
                    'sample_query_time': round(query_time * 1000, 2)  # ms
                }
        except Exception as e:
            return {'error': str(e)}

    def get_application_metrics(self):
        """Get application-specific metrics"""
        try:
            from orders.models import Order
            from inventory.models import InventoryItem

            # Order metrics
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status='pending').count()
            processing_orders = Order.objects.filter(status='processing').count()

            # Inventory metrics
            total_inventory = InventoryItem.objects.count()
            low_stock_items = InventoryItem.objects.filter(quantity__lte=10).count()

            return {
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'processing_orders': processing_orders,
                'total_inventory_items': total_inventory,
                'low_stock_items': low_stock_items
            }
        except Exception as e:
            return {'error': str(e)}

    def display_sample(self, sample):
        """Display a sample in real-time"""
        timestamp = sample['timestamp'][:19]  # Remove microseconds

        self.stdout.write(
            f"{timestamp} | "
            f"CPU: {sample['cpu_percent']:5.1f}% | "
            f"RAM: {sample['memory_percent']:5.1f}% | "
            f"Disk: {sample['disk_percent']:5.1f}% | "
            f"DB Conn: {sample['database'].get('active_connections', 'N/A')} | "
            f"Pending Orders: {sample['application'].get('pending_orders', 'N/A')}"
        )

    def generate_summary(self, data):
        """Generate performance summary statistics"""
        if not data:
            return {}

        # CPU statistics
        cpu_values = [s['cpu_percent'] for s in data]
        memory_values = [s['memory_percent'] for s in data]
        disk_values = [s['disk_percent'] for s in data]

        # Database query times
        query_times = [
            s['database'].get('sample_query_time', 0)
            for s in data
            if 'sample_query_time' in s['database']
        ]

        summary = {
            'monitoring_period': {
                'start': data[0]['timestamp'],
                'end': data[-1]['timestamp'],
                'duration_seconds': len(data) * 5,  # Approximate
                'samples_collected': len(data)
            },
            'cpu': {
                'average': round(sum(cpu_values) / len(cpu_values), 2),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'average': round(sum(memory_values) / len(memory_values), 2),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'disk': {
                'average': round(sum(disk_values) / len(disk_values), 2),
                'max': max(disk_values),
                'min': min(disk_values)
            }
        }

        if query_times:
            summary['database_performance'] = {
                'average_query_time_ms': round(sum(query_times) / len(query_times), 2),
                'max_query_time_ms': max(query_times),
                'min_query_time_ms': min(query_times)
            }

        return summary

    def display_summary(self, summary):
        """Display performance summary"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('PERFORMANCE SUMMARY')
        self.stdout.write('=' * 60)

        period = summary['monitoring_period']
        self.stdout.write(f"Monitoring Period: {period['start']} to {period['end']}")
        self.stdout.write(f"Duration: {period['duration_seconds']} seconds ({period['samples_collected']} samples)")
        self.stdout.write('')

        # CPU Summary
        cpu = summary['cpu']
        self.stdout.write(f"CPU Usage:")
        self.stdout.write(f"  Average: {cpu['average']}%")
        self.stdout.write(f"  Range: {cpu['min']}% - {cpu['max']}%")

        # Memory Summary
        memory = summary['memory']
        self.stdout.write(f"\nMemory Usage:")
        self.stdout.write(f"  Average: {memory['average']}%")
        self.stdout.write(f"  Range: {memory['min']}% - {memory['max']}%")

        # Disk Summary
        disk = summary['disk']
        self.stdout.write(f"\nDisk Usage:")
        self.stdout.write(f"  Average: {disk['average']}%")
        self.stdout.write(f"  Range: {disk['min']}% - {disk['max']}%")

        # Database Performance
        if 'database_performance' in summary:
            db = summary['database_performance']
            self.stdout.write(f"\nDatabase Performance:")
            self.stdout.write(f"  Average Query Time: {db['average_query_time_ms']} ms")
            self.stdout.write(f"  Query Time Range: {db['min_query_time_ms']} - {db['max_query_time_ms']} ms")

        # Performance Assessment
        self.stdout.write(f"\nPerformance Assessment:")
        self.assess_performance(summary)

    def assess_performance(self, summary):
        """Provide performance assessment"""
        issues = []

        # Check CPU
        if summary['cpu']['average'] > 80:
            issues.append("⚠ High CPU usage detected")
        elif summary['cpu']['average'] > 50:
            issues.append("⚠ Moderate CPU usage")

        # Check Memory
        if summary['memory']['average'] > 90:
            issues.append("⚠ Very high memory usage")
        elif summary['memory']['average'] > 70:
            issues.append("⚠ High memory usage")

        # Check Disk
        if summary['disk']['average'] > 90:
            issues.append("⚠ Very high disk usage")
        elif summary['disk']['average'] > 80:
            issues.append("⚠ High disk usage")

        # Check Database
        if 'database_performance' in summary:
            avg_query_time = summary['database_performance']['average_query_time_ms']
            if avg_query_time > 100:
                issues.append("⚠ Slow database queries detected")

        if issues:
            for issue in issues:
                self.stdout.write(f"  {issue}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ System performance appears healthy"))

    def save_results(self, data, summary, filename):
        """Save performance results to file"""
        results = {
            'performance_data': data,
            'summary': summary,
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'command_version': '1.0'
            }
        }

        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)