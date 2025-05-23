from django.db import models
from django.utils import timezone
from products.models import Product
from core.models import BaseModel
import uuid


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    SHIPPED = 'shipped', 'Shipped'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'
    FAILED = 'failed', 'Failed'


class Order(BaseModel):
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True
    )
    current_state_since = models.DateTimeField(default=timezone.now)
    version = models.PositiveIntegerField(default=1, editable=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Additional fields for better tracking
    shipping_address = models.TextField(blank=True)
    billing_address = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    priority = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')],
        default='normal'
    )

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['status', 'current_state_since']),
            models.Index(fields=['customer_email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['priority', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_id} - {self.status}"

    def update_status(self, new_status, notes=""):
        """Update order status and record transition"""
        if self.status == new_status:
            return False  # No change needed

        old_status = self.status
        self.status = new_status
        self.current_state_since = timezone.now()
        self.version += 1

        # Set timestamps based on status
        if new_status == OrderStatus.PROCESSING and not self.processing_started_at:
            self.processing_started_at = timezone.now()
        elif new_status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
            if not self.completed_at:
                self.completed_at = timezone.now()

        self.save()

        # Record the state transition
        OrderStatusHistory.objects.create(
            order=self,
            from_status=old_status,
            to_status=new_status,
            notes=notes
        )
        return True

    def calculate_total(self):
        """Calculate and update the total amount"""
        total = sum(item.quantity * item.price for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

    @property
    def is_stale(self):
        """Check if order has been in current state too long"""
        from datetime import timedelta

        # Define thresholds for each status (in minutes)
        thresholds = {
            OrderStatus.PENDING: 5,  # 5 minutes
            OrderStatus.PROCESSING: 10,  # 10 minutes
            OrderStatus.SHIPPED: 60,  # 1 hour
        }

        if self.status not in thresholds:
            return False

        threshold_minutes = thresholds[self.status]
        time_threshold = timezone.now() - timedelta(minutes=threshold_minutes)
        return self.current_state_since < time_threshold


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'
        unique_together = ['order', 'product']  # Prevent duplicate products in same order
        indexes = [
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name} @ ${self.price}"

    @property
    def total_price(self):
        return self.quantity * self.price


class OrderStatusHistory(BaseModel):
    order = models.ForeignKey(Order, related_name='status_history', on_delete=models.CASCADE)
    from_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    to_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    notes = models.TextField(blank=True)
    processed_by = models.CharField(max_length=100, default='system')
    processing_time_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['from_status', 'to_status']),
        ]

    def __str__(self):
        return f"{self.order.order_id}: {self.from_status} → {self.to_status}"


class OrderBatch(BaseModel):
    """For tracking bulk order operations"""
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    total_orders = models.PositiveIntegerField()
    successful_orders = models.PositiveIntegerField(default=0)
    failed_orders = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='processing'
    )

    class Meta:
        db_table = 'order_batches'

    def __str__(self):
        return f"Batch {self.batch_id} - {self.successful_orders}/{self.total_orders} successful"