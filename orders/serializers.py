from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem, OrderStatusHistory, OrderBatch
from products.models import Product
from inventory.models import InventoryItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        source='product',
        write_only=True
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['product_id', 'product_name', 'product_sku', 'quantity', 'price', 'total_price']
        read_only_fields = ['price', 'total_price']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'customer_name', 'customer_email', 'items',
            'shipping_address', 'billing_address', 'payment_method', 'priority'
        ]

    def validate_items(self, items_data):
        if not items_data:
            raise serializers.ValidationError("At least one item is required.")

        # Check for duplicate products
        product_ids = [item['product'].id for item in items_data]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError("Duplicate products are not allowed in the same order.")

        # Validate stock availability
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            try:
                inventory = InventoryItem.objects.get(product=product)
                if inventory.available_quantity < quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. "
                        f"Available: {inventory.available_quantity}, Requested: {quantity}"
                    )
            except InventoryItem.DoesNotExist:
                raise serializers.ValidationError(f"No inventory found for product: {product.name}")

        return items_data

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        # Create order items and reserve inventory
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            # Create order item with current product price
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price
            )

            # Reserve inventory
            success = InventoryItem.reserve_stock(product.id, quantity)
            if not success:
                raise serializers.ValidationError(
                    f"Failed to reserve stock for {product.name}"
                )

        return order


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = [
            'from_status', 'to_status', 'notes', 'processed_by',
            'processing_time_seconds', 'duration_minutes', 'created_at'
        ]

    def get_duration_minutes(self, obj):
        if obj.processing_time_seconds:
            return round(obj.processing_time_seconds / 60, 2)
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    time_in_current_status = serializers.SerializerMethodField()
    is_stale = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'order_id', 'customer_name', 'customer_email', 'status',
            'total_amount', 'priority', 'shipping_address', 'billing_address',
            'payment_method', 'tracking_number', 'processing_started_at',
            'completed_at', 'current_state_since', 'time_in_current_status',
            'version', 'is_stale', 'items', 'status_history',
            'created_at', 'updated_at'
        ]

    def get_items(self, obj):
        items = OrderItem.objects.filter(order=obj).select_related('product')
        return [{
            'product_id': item.product_id,
            'product_name': item.product.name,
            'product_sku': item.product.sku,
            'quantity': item.quantity,
            'price': str(item.price),
            'total_price': str(item.total_price)
        } for item in items]

    def get_time_in_current_status(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.current_state_since
        return {
            'total_seconds': int(delta.total_seconds()),
            'minutes': round(delta.total_seconds() / 60, 1),
            'human_readable': str(delta).split('.')[0]  # Remove microseconds
        }


class OrderListSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    time_in_current_status_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_id', 'customer_name', 'customer_email', 'status',
            'total_amount', 'priority', 'items_count', 'current_state_since',
            'time_in_current_status_minutes', 'is_stale', 'created_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_time_in_current_status_minutes(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.current_state_since
        return round(delta.total_seconds() / 60, 1)


class BulkOrderCreateSerializer(serializers.Serializer):
    orders = OrderCreateSerializer(many=True)

    def validate_orders(self, orders_data):
        if not orders_data:
            raise serializers.ValidationError("At least one order is required.")

        if len(orders_data) > 100:
            raise serializers.ValidationError("Cannot create more than 100 orders at once.")

        return orders_data

    @transaction.atomic
    def create(self, validated_data):
        orders_data = validated_data['orders']
        created_orders = []

        # Create order batch for tracking
        batch = OrderBatch.objects.create(
            total_orders=len(orders_data)
        )

        try:
            for order_data in orders_data:
                serializer = OrderCreateSerializer(data=order_data)
                serializer.is_valid(raise_exception=True)
                order = serializer.save()
                created_orders.append(order)
                batch.successful_orders += 1

            batch.status = 'completed'
            batch.save()

        except Exception as e:
            batch.failed_orders = len(orders_data) - len(created_orders)
            batch.status = 'failed'
            batch.save()
            raise e

        return {
            'batch_id': batch.batch_id,
            'created_orders': created_orders,
            'total_orders': len(created_orders)
        }
