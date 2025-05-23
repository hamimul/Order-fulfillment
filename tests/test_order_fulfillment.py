import json
import time
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed
from products.models import Product
from inventory.models import InventoryItem, InventoryTransaction
from orders.models import Order, OrderStatus, OrderItem


class ProductAPITestCase(TestCase):
    """Test cases for Product API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.product1 = Product.objects.create(
            name="Test Product 1",
            sku="TEST-001",
            price=Decimal("99.99"),
            description="Test product description"
        )
        self.product2 = Product.objects.create(
            name="Test Product 2",
            sku="TEST-002",
            price=Decimal("149.99"),
            description="Another test product"
        )

    def test_list_products(self):
        """Test listing all products"""
        url = reverse('product-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_product_detail(self):
        """Test getting product detail"""
        url = reverse('product-detail', kwargs={'pk': self.product1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Test Product 1")
        self.assertEqual(response.data['sku'], "TEST-001")

    def test_create_product(self):
        """Test creating a new product"""
        url = reverse('product-list')
        data = {
            'name': 'New Product',
            'sku': 'NEW-001',
            'price': '199.99',
            'description': 'New product description',
            'initial_stock': 100
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that inventory was created
        product = Product.objects.get(sku='NEW-001')
        self.assertTrue(hasattr(product, 'inventory'))
        self.assertEqual(product.inventory.quantity, 100)


class InventoryTestCase(TestCase):
    """Test cases for inventory management"""

    def setUp(self):
        self.product = Product.objects.create(
            name="Inventory Test Product",
            sku="INV-001",
            price=Decimal("50.00")
        )
        # Inventory is created automatically by signal
        self.inventory = InventoryItem.objects.get(product=self.product)
        self.inventory.quantity = 100
        self.inventory.save()

    def test_reserve_stock_success(self):
        """Test successful stock reservation"""
        success = InventoryItem.reserve_stock(self.product.id, 10)

        self.assertTrue(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 10)
        self.assertEqual(self.inventory.available_quantity, 90)

    def test_reserve_stock_insufficient(self):
        """Test stock reservation with insufficient quantity"""
        success = InventoryItem.reserve_stock(self.product.id, 150)

        self.assertFalse(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 0)

    def test_release_stock(self):
        """Test releasing reserved stock"""
        # First reserve some stock
        InventoryItem.reserve_stock(self.product.id, 20)

        # Then release it
        success = InventoryItem.release_stock(self.product.id, 15)

        self.assertTrue(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.reserved_quantity, 5)

    def test_fulfill_order(self):
        """Test fulfilling an order (reducing both total and reserved)"""
        # Reserve stock first
        InventoryItem.reserve_stock(self.product.id, 30)

        # Fulfill part of the order
        success = InventoryItem.fulfill_order(self.product.id, 25)

        self.assertTrue(success)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 75)  # Total reduced
        self.assertEqual(self.inventory.reserved_quantity, 5)  # Reserved reduced

    def test_inventory_transaction_logging(self):
        """Test that inventory transactions are properly logged"""
        initial_count = InventoryTransaction.objects.count()

        InventoryItem.reserve_stock(self.product.id, 15)

        # Check that a transaction was logged
        self.assertEqual(InventoryTransaction.objects.count(), initial_count + 1)

        transaction = InventoryTransaction.objects.latest('created_at')
        self.assertEqual(transaction.transaction_type, InventoryTransaction.RESERVE)
        self.assertEqual(transaction.quantity, 15)


class OrderProcessingTestCase(TransactionTestCase):
    """Test cases for order processing - using TransactionTestCase for signal testing"""

    def setUp(self):
        self.client = APIClient()

        # Create test products with inventory
        self.product1 = Product.objects.create(
            name="Order Test Product 1",
            sku="ORD-001",
            price=Decimal("25.00")
        )
        self.product2 = Product.objects.create(
            name="Order Test Product 2",
            sku="ORD-002",
            price=Decimal("35.00")
        )

        # Set up inventory
        inventory1 = InventoryItem.objects.get(product=self.product1)
        inventory1.quantity = 100
        inventory1.save()

        inventory2 = InventoryItem.objects.get(product=self.product2)
        inventory2.quantity = 50
        inventory2.save()

    def test_create_order_success(self):
        """Test successful order creation"""
        url = reverse('order-list')
        data = {
            'customer_name': 'Test Customer',
            'customer_email': 'test@example.com',
            'items': [
                {'product_id': self.product1.id, 'quantity': 2},
                {'product_id': self.product2.id, 'quantity': 1}
            ]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify order was created
        order = Order.objects.get(order_id=response.data['order_id'])
        self.assertEqual(order.items.count(), 2)

        # Verify inventory was reserved
        inventory1 = InventoryItem.objects.get(product=self.product1)
        inventory2 = InventoryItem.objects.get(product=self.product2)

        self.assertEqual(inventory1.reserved_quantity, 2)
        self.assertEqual(inventory2.reserved_quantity, 1)

    def test_create_order_insufficient_stock(self):
        """Test order creation with insufficient stock"""
        url = reverse('order-list')
        data = {
            'customer_name': 'Test Customer',
            'customer_email': 'test@example.com',
            'items': [
                {'product_id': self.product1.id, 'quantity': 150}  # More than available
            ]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', str(response.data))

    def test_cancel_order_releases_inventory(self):
        """Test that cancelling an order releases reserved inventory"""
        # Create an order first
        order = Order.objects.create(
            customer_name="Cancel Test",
            customer_email="cancel@test.com"
        )

        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=5,
            price=self.product1.price
        )

        # Reserve inventory
        InventoryItem.reserve_stock(self.product1.id, 5)

        # Cancel the order
        order.update_status(OrderStatus.CANCELLED)

        # Check that inventory was released
        inventory = InventoryItem.objects.get(product=self.product1)
        self.assertEqual(inventory.reserved_quantity, 0)

    def test_bulk_order_creation(self):
        """Test bulk order creation endpoint"""
        url = reverse('order-bulk-create')
        data = {
            'orders': [
                {
                    'customer_name': f'Bulk Customer {i}',
                    'customer_email': f'bulk{i}@test.com',
                    'items': [{'product_id': self.product1.id, 'quantity': 1}]
                }
                for i in range(5)
            ]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['order_ids']), 5)

        # Verify inventory was reserved for all orders
        inventory = InventoryItem.objects.get(product=self.product1)
        self.assertEqual(inventory.reserved_quantity, 5)


class ConcurrencyTestCase(TransactionTestCase):
    """Test concurrent order processing"""

    def setUp(self):
        self.client = APIClient()

        # Create a product with limited stock
        self.product = Product.objects.create(
            name="Concurrency Test Product",
            sku="CONC-001",
            price=Decimal("10.00")
        )

        inventory = InventoryItem.objects.get(product=self.product)
        inventory.quantity = 10  # Limited stock for concurrency testing
        inventory.save()

    def test_concurrent_order_creation(self):
        """Test that concurrent orders don't oversell inventory"""

        def create_order(customer_num):
            url = reverse('order-list')
            data = {
                'customer_name': f'Concurrent Customer {customer_num}',
                'customer_email': f'concurrent{customer_num}@test.com',
                'items': [{'product_id': self.product.id, 'quantity': 2}]
            }

            try:
                response = self.client.post(url, data, format='json')
                return response.status_code == status.HTTP_201_CREATED
            except Exception:
                return False

        # Try to create 10 orders concurrently, each wanting 2 units
        # Only 5 should succeed (10 units / 2 units per order)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_order, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        successful_orders = sum(results)

        # Should have exactly 5 successful orders (using all 10 units)
        self.assertEqual(successful_orders, 5)

        # Verify inventory state
        inventory = InventoryItem.objects.get(product=self.product)
        self.assertEqual(inventory.reserved_quantity, 10)
        self.assertEqual(inventory.available_quantity, 0)


class OrderVersioningTestCase(TestCase):
    """Test order versioning and history tracking"""

    def setUp(self):
        self.product = Product.objects.create(
            name="Version Test Product",
            sku="VER-001",
            price=Decimal("20.00")
        )

        inventory = InventoryItem.objects.get(product=self.product)
        inventory.quantity = 100
        inventory.save()

        self.order = Order.objects.create(
            customer_name="Version Test Customer",
            customer_email="version@test.com"
        )

    def test_order_version_increment(self):
        """Test that order version increments on status changes"""
        initial_version = self.order.version

        self.order.update_status(OrderStatus.PROCESSING)
        self.assertEqual(self.order.version, initial_version + 1)

        self.order.update_status(OrderStatus.SHIPPED)
        self.assertEqual(self.order.version, initial_version + 2)

    def test_order_history_tracking(self):
        """Test that order status changes are tracked in history"""
        # Change status multiple times
        self.order.update_status(OrderStatus.PROCESSING, "Started processing")
        self.order.update_status(OrderStatus.SHIPPED, "Order shipped")
        self.order.update_status(OrderStatus.DELIVERED, "Order delivered")

        # Check history count
        history_count = self.order.status_history.count()
        self.assertEqual(history_count, 3)

        # Check history order (most recent first)
        latest_history = self.order.status_history.first()
        self.assertEqual(latest_history.to_status, OrderStatus.DELIVERED)
        self.assertEqual(latest_history.from_status, OrderStatus.SHIPPED)

    def test_order_history_api_endpoint(self):
        """Test the order history API endpoint"""
        # Create some history
        self.order.update_status(OrderStatus.PROCESSING)
        self.order.update_status(OrderStatus.SHIPPED)

        client = APIClient()
        url = reverse('order-history', kwargs={'order_id': self.order.order_id})
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


class APIDocumentationTestCase(TestCase):
    """Test API documentation endpoints"""

    def test_swagger_ui_accessible(self):
        """Test that Swagger UI is accessible"""
        response = self.client.get('/swagger/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_redoc_accessible(self):
        """Test that ReDoc is accessible"""
        response = self.client.get('/redoc/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible"""
        response = self.client.get('/swagger.json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify it's valid JSON
        schema = response.json()
        self.assertIn('openapi', schema)
        self.assertIn('info', schema)
        self.assertIn('paths', schema)


class HealthCheckTestCase(TestCase):
    """Test system health check endpoint"""

    def test_health_check_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])


class StaleOrderTestCase(TestCase):
    """Test stale order detection and handling"""

    def setUp(self):
        self.product = Product.objects.create(
            name="Stale Test Product",
            sku="STALE-001",
            price=Decimal("15.00")
        )

        inventory = InventoryItem.objects.get(product=self.product)
        inventory.quantity = 100
        inventory.save()

    def test_stale_order_detection(self):
        """Test that orders can be identified as stale"""
        from django.utils import timezone
        from datetime import timedelta

        # Create an order and manually set its state time to the past
        order = Order.objects.create(
            customer_name="Stale Test Customer",
            customer_email="stale@test.com",
            status=OrderStatus.PROCESSING
        )

        # Manually set the state time to 15 minutes ago
        order.current_state_since = timezone.now() - timedelta(minutes=15)
        order.save()

        # Check if order is detected as stale
        self.assertTrue(order.is_stale)

    def test_stale_order_check_api(self):
        """Test the manual stale order check API endpoint"""
        client = APIClient()
        url = reverse('order-check-stale')
        response = client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)