from django.db import models, transaction
from django.core.exceptions import ValidationError
from products.models import Product
from core.models import BaseModel
import uuid


class InventoryItem(BaseModel):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    minimum_threshold = models.PositiveIntegerField(default=10)
    maximum_capacity = models.PositiveIntegerField(default=1000)

    class Meta:
        db_table = 'inventory_items'
        indexes = [
            models.Index(fields=['quantity']),
            models.Index(fields=['reserved_quantity']),
        ]

    def __str__(self):
        return f"{self.product.name} - Available: {self.available_quantity} (Total: {self.quantity})"

    @property
    def available_quantity(self):
        """Get the actual available quantity (total - reserved)"""
        return max(0, self.quantity - self.reserved_quantity)

    @classmethod
    def reserve_stock(cls, product_id, quantity):
        """Reserve stock with proper locking to handle concurrency"""
        with transaction.atomic():
            # Select for update locks the row
            try:
                inventory = cls.objects.select_for_update().get(product_id=product_id)

                if inventory.available_quantity >= quantity:
                    inventory.reserved_quantity += quantity
                    inventory.save()

                    # Create transaction record
                    InventoryTransaction.objects.create(
                        inventory_item=inventory,
                        transaction_type=InventoryTransaction.RESERVE,
                        quantity=quantity,
                        previous_quantity=inventory.quantity,
                        new_quantity=inventory.quantity,
                        previous_reserved=inventory.reserved_quantity - quantity,
                        new_reserved=inventory.reserved_quantity,
                        notes=f"Reserved {quantity} units"
                    )
                    return True
                return False
            except cls.DoesNotExist:
                return False

    @classmethod
    def release_stock(cls, product_id, quantity, order_id=None):
        """Release reserved stock back to available inventory"""
        with transaction.atomic():
            try:
                inventory = cls.objects.select_for_update().get(product_id=product_id)

                if inventory.reserved_quantity >= quantity:
                    inventory.reserved_quantity -= quantity
                    inventory.save()

                    # Create transaction record
                    InventoryTransaction.objects.create(
                        inventory_item=inventory,
                        transaction_type=InventoryTransaction.RELEASE,
                        quantity=quantity,
                        previous_quantity=inventory.quantity,
                        new_quantity=inventory.quantity,
                        previous_reserved=inventory.reserved_quantity + quantity,
                        new_reserved=inventory.reserved_quantity,
                        order_id=order_id,
                        notes=f"Released {quantity} units"
                    )
                    return True
                return False
            except cls.DoesNotExist:
                return False

    @classmethod
    def fulfill_order(cls, product_id, quantity, order_id=None):
        """Fulfill an order by reducing both reserved and total quantity"""
        with transaction.atomic():
            try:
                inventory = cls.objects.select_for_update().get(product_id=product_id)

                if inventory.reserved_quantity >= quantity:
                    inventory.quantity -= quantity
                    inventory.reserved_quantity -= quantity
                    inventory.save()

                    # Create transaction record
                    InventoryTransaction.objects.create(
                        inventory_item=inventory,
                        transaction_type=InventoryTransaction.FULFILL,
                        quantity=quantity,
                        previous_quantity=inventory.quantity + quantity,
                        new_quantity=inventory.quantity,
                        previous_reserved=inventory.reserved_quantity + quantity,
                        new_reserved=inventory.reserved_quantity,
                        order_id=order_id,
                        notes=f"Fulfilled order for {quantity} units"
                    )
                    return True
                return False
            except cls.DoesNotExist:
                return False


class InventoryTransaction(BaseModel):
    """Detailed log of all inventory changes"""

    RESERVE = 'RESERVE'
    RELEASE = 'RELEASE'
    FULFILL = 'FULFILL'
    ADJUST = 'ADJUST'
    RECEIVE = 'RECEIVE'
    DAMAGE = 'DAMAGE'

    TRANSACTION_TYPES = [
        (RESERVE, 'Reserve Stock'),
        (RELEASE, 'Release Stock'),
        (FULFILL, 'Fulfill Order'),
        (ADJUST, 'Adjust Stock'),
        (RECEIVE, 'Receive Stock'),
        (DAMAGE, 'Damage/Loss'),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField()
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    previous_reserved = models.PositiveIntegerField(default=0)
    new_reserved = models.PositiveIntegerField(default=0)
    order_id = models.UUIDField(null=True, blank=True, db_index=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    processed_by = models.CharField(max_length=100, default='system')

    class Meta:
        db_table = 'inventory_transactions'
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['order_id']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.quantity} units of {self.inventory_item.product.name}"