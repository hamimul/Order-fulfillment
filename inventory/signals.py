from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from products.models import Product
from .models import InventoryItem, InventoryTransaction
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def create_inventory_item(sender, instance, created, **kwargs):
    """Automatically create inventory item when a new product is created"""
    if created:
        inventory_item = InventoryItem.objects.create(
            product=instance,
            quantity=0,
            reserved_quantity=0
        )
        logger.info(f"Created inventory item for product: {instance.name}")


@receiver(pre_save, sender=InventoryItem)
def track_inventory_changes(sender, instance, **kwargs):
    """Track inventory changes for audit purposes"""
    # Only run for existing instances (not new ones)
    if instance.pk:
        try:
            previous_instance = InventoryItem.objects.get(pk=instance.pk)

            # Store previous values for comparison in post_save
            instance._previous_quantity = previous_instance.quantity
            instance._previous_reserved = previous_instance.reserved_quantity
            instance._has_changes = (
                    previous_instance.quantity != instance.quantity or
                    previous_instance.reserved_quantity != instance.reserved_quantity
            )

        except InventoryItem.DoesNotExist:
            instance._has_changes = False


@receiver(post_save, sender=InventoryItem)
def log_inventory_changes(sender, instance, created, **kwargs):
    """Log inventory changes after save"""
    if not created and hasattr(instance, '_has_changes') and instance._has_changes:

        # Check if quantity changed (not through our reserve/release methods)
        if (hasattr(instance, '_previous_quantity') and
                instance._previous_quantity != instance.quantity):

            quantity_change = instance.quantity - instance._previous_quantity
            transaction_type = InventoryTransaction.RECEIVE if quantity_change > 0 else InventoryTransaction.ADJUST

            # Only create transaction if it wasn't created by our methods
            # (our methods create their own transactions)
            recent_transactions = InventoryTransaction.objects.filter(
                inventory_item=instance,
                new_quantity=instance.quantity,
                new_reserved=instance.reserved_quantity
            ).count()

            if recent_transactions == 0:
                InventoryTransaction.objects.create(
                    inventory_item=instance,
                    transaction_type=transaction_type,
                    quantity=abs(quantity_change),
                    previous_quantity=instance._previous_quantity,
                    new_quantity=instance.quantity,
                    previous_reserved=getattr(instance, '_previous_reserved', 0),
                    new_reserved=instance.reserved_quantity,
                    notes=f"Manual adjustment via admin or signal",
                    processed_by='system'
                )

                logger.info(f"Logged inventory change for {instance.product.name}: "
                            f"{instance._previous_quantity} → {instance.quantity}")


@receiver(post_save, sender=InventoryTransaction)
def check_low_stock_alert(sender, instance, created, **kwargs):
    """Check for low stock after inventory transactions"""
    if created:
        inventory_item = instance.inventory_item

        # Alert if available quantity is below threshold
        if inventory_item.available_quantity <= inventory_item.minimum_threshold:
            logger.warning(f"LOW STOCK ALERT: {inventory_item.product.name} "
                           f"has only {inventory_item.available_quantity} units available "
                           f"(threshold: {inventory_item.minimum_threshold})")

            # Here you could send emails, create notifications, etc.
            # For now, we'll just log it