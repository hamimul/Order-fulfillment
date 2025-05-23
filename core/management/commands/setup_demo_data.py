from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from products.models import Product
from inventory.models import InventoryItem
import random


class Command(BaseCommand):
    help = 'Sets up demo products and inventory data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            type=int,
            default=20,
            help='Number of products to create (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared all existing products and inventory'))

        self.stdout.write('Creating demo products and inventory...')

        # Product categories and names
        categories = {
            'Electronics': [
                'Smartphone X Pro', 'Wireless Earbuds Pro', 'Smart Watch Series 5',
                'Laptop Ultra 15"', 'Tablet Air 10"', 'Gaming Console Elite',
                'Bluetooth Speaker Max', 'Wireless Charger Fast', '4K Webcam HD',
                'USB-C Hub Premium'
            ],
            'Clothing': [
                'Cotton T-Shirt Premium', 'Denim Jeans Classic', 'Hoodie Comfort',
                'Running Shoes Pro', 'Winter Jacket Warm', 'Baseball Cap Classic',
                'Socks Cotton Pack', 'Belt Leather Brown', 'Polo Shirt Business',
                'Sneakers Urban Style'
            ],
            'Home & Garden': [
                'Coffee Maker Deluxe', 'Vacuum Cleaner Robot', 'Air Purifier HEPA',
                'Plant Pot Ceramic', 'LED Desk Lamp', 'Kitchen Knife Set',
                'Throw Pillow Soft', 'Candle Scented Vanilla', 'Picture Frame Wood',
                'Storage Box Plastic'
            ],
            'Sports': [
                'Yoga Mat Premium', 'Dumbbells Set 20kg', 'Resistance Bands',
                'Tennis Racket Pro', 'Football Official', 'Basketball Indoor',
                'Swimming Goggles', 'Bicycle Helmet Safety', 'Running Shorts',
                'Protein Shaker Bottle'
            ]
        }

        products_created = 0
        target_products = options['products']

        with transaction.atomic():
            # Create products from categories
            for category, product_names in categories.items():
                if products_created >= target_products:
                    break

                for product_name in product_names:
                    if products_created >= target_products:
                        break

                    # Generate SKU
                    sku = f"{category[:3].upper()}-{random.randint(1000, 9999)}"

                    # Ensure SKU is unique
                    while Product.objects.filter(sku=sku).exists():
                        sku = f"{category[:3].upper()}-{random.randint(1000, 9999)}"

                    # Generate realistic price based on category
                    price_ranges = {
                        'Electronics': (50, 1500),
                        'Clothing': (15, 200),
                        'Home & Garden': (10, 300),
                        'Sports': (20, 250)
                    }

                    min_price, max_price = price_ranges[category]
                    price = round(random.uniform(min_price, max_price), 2)

                    # Create product
                    product = Product.objects.create(
                        name=product_name,
                        description=f"High-quality {product_name.lower()} from the {category} category. "
                                    f"Perfect for everyday use with excellent durability and performance.",
                        price=price,
                        sku=sku,
                        is_active=True
                    )

                    # Create inventory (this will be created automatically by signal,
                    # but we'll update it with realistic quantities)
                    inventory = InventoryItem.objects.get(product=product)

                    # Set realistic inventory levels
                    base_quantity = random.randint(50, 500)
                    reserved_quantity = random.randint(0, min(base_quantity // 10, 20))

                    inventory.quantity = base_quantity
                    inventory.reserved_quantity = reserved_quantity
                    inventory.minimum_threshold = max(10, base_quantity // 20)
                    inventory.maximum_capacity = base_quantity * 2
                    inventory.save()

                    products_created += 1

                    if products_created % 5 == 0:
                        self.stdout.write(f'Created {products_created} products...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {products_created} products with inventory!'
            )
        )

        # Display summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('DEMO DATA SUMMARY')
        self.stdout.write('=' * 50)

        total_products = Product.objects.count()
        total_inventory_value = sum(
            p.price * p.inventory.quantity for p in Product.objects.all()
        )
        low_stock_items = InventoryItem.objects.filter(
            quantity__lte=F('minimum_threshold')
        ).count()

        self.stdout.write(f'Total Products: {total_products}')
        self.stdout.write(f'Total Inventory Value: ${total_inventory_value:,.2f}')
        self.stdout.write(f'Low Stock Items: {low_stock_items}')

        # Show some sample products
        self.stdout.write('\nSample Products:')
        for product in Product.objects.all()[:5]:
            self.stdout.write(
                f'  • {product.name} ({product.sku}) - '
                f'${product.price} - Stock: {product.inventory.available_quantity}'
            )

        self.stdout.write('\n' + self.style.SUCCESS('Demo data setup complete!'))