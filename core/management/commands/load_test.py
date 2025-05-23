from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from products.models import Product
from orders.models import Order, OrderItem
from inventory.models import InventoryItem
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class Command(BaseCommand):
    help = 'Run load test by creating multiple orders concurrently'

    def add_arguments(self, parser):
        parser.add_argument(
            '--orders',
            type=int,
            default=50,
            help='Number of orders to create (default: 50)'
        )
        parser.add_argument(
            '--threads',
            type=int,
            default=5,
            help='Number of concurrent threads (default: 5)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.1,
            help='Delay between orders in seconds (default: 0.1)'
        )

    def handle(self, *args, **options):
        num_orders = options['orders']
        num_threads = options['threads']
        delay = options['delay']

        self.stdout.write(f'Starting load test with {num_orders} orders using {num_threads} threads...')

        # Get available products
        products = list(Product.objects.filter(
            is_active=True,
            inventory__available_quantity__gt=0
        ))

        if not products:
            self.stdout.write(self.style.ERROR('No products available for testing!'))
            return

        self.stdout.write(f'Found {len(products)} products available for testing')

        # Statistics tracking
        stats = {
            'created': 0,
            'failed': 0,
            'start_time': timezone.now(),
            'lock': threading.Lock()
        }

        def create_order(order_num):
            """Create a single order"""
            try:
                # Random customer data
                customer_name = f"Test Customer {order_num}"
                customer_email = f"customer{order_num}@test.com"

                # Select random products (1-5 items per order)
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))

                with transaction.atomic():
                    # Create order
                    order = Order.objects.create(
                        customer_name=customer_name,
                        customer_email=customer_email,
                        priority=random.choice(['low', 'normal', 'high']),
                        shipping_address=f"123 Test St, City {order_num}",
                        payment_method='credit_card'
                    )

                    # Add items to order
                    total_amount = 0
                    for product in selected_products:
                        quantity = random.randint(1, 3)

                        # Check and reserve inventory
                        if InventoryItem.reserve_stock(product.id, quantity):
                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                quantity=quantity,
                                price=product.price
                            )
                            total_amount += product.price * quantity
                        else:
                            # If we can't reserve stock, try with quantity 1
                            if InventoryItem.reserve_stock(product.id, 1):
                                OrderItem.objects.create(
                                    order=order,
                                    product=product,
                                    quantity=1,
                                    price=product.price
                                )
                                total_amount += product.price

                    # Update total amount
                    order.total_amount = total_amount
                    order.save()

                with stats['lock']:
                    stats['created'] += 1
                    if stats['created'] % 10 == 0:
                        elapsed = (timezone.now() - stats['start_time']).total_seconds()
                        rate = stats['created'] / elapsed
                        self.stdout.write(f'Created {stats["created"]} orders (Rate: {rate:.2f} orders/sec)')

                return True

            except Exception as e:
                with stats['lock']:
                    stats['failed'] += 1
                self.stdout.write(self.style.ERROR(f'Failed to create order {order_num}: {str(e)}'))
                return False

        # Execute load test
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all order creation tasks
            futures = []
            for i in range(num_orders):
                future = executor.submit(create_order, i + 1)
                futures.append(future)

                # Add delay between submissions if specified
                if delay > 0:
                    time.sleep(delay)

            # Wait for all tasks to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Thread error: {str(e)}'))

        # Calculate final statistics
        end_time = time.time()
        total_time = end_time - start_time

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('LOAD TEST RESULTS')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total Time: {total_time:.2f} seconds')
        self.stdout.write(f'Orders Created: {stats["created"]}')
        self.stdout.write(f'Orders Failed: {stats["failed"]}')
        self.stdout.write(f'Success Rate: {(stats["created"] / num_orders) * 100:.1f}%')
        self.stdout.write(f'Average Rate: {stats["created"] / total_time:.2f} orders/second')
        self.stdout.write(f'Threads Used: {num_threads}')

        if stats["created"] > 0:
            self.stdout.write(self.style.SUCCESS(f'\nLoad test completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR(f'\nLoad test failed - no orders created!'))