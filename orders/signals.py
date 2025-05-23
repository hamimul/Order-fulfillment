from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Order, OrderStatus, OrderItem
from inventory.models import InventoryItem
from .tasks import process_order
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def order_created_or_updated(sender, instance, created, **kwargs):
    """Handle order creation and status updates"""
    if created:
        logger.info(f"New order created: {instance.order_id}")
        # Calculate total amount
        instance.calculate_total()

        # Start async processing after a short delay to ensure all order items are saved
        process_order.apply_async(args=[str(instance.order_id)], countdown=2)

    else:
        # Handle status changes
        if instance.status in [OrderStatus.CANCELLED, OrderStatus.FAILED]:
            logger.info(f"Order {instance.order_id} status changed to {instance.status}")
            # Release inventory will be handled by the status change signal below


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """Handle order status changes and inventory updates"""
    if not created:
        # Check if this is a cancellation or failure
        if instance.status in [OrderStatus.CANCELLED, OrderStatus.FAILED]:
            # Release all reserved inventory for this order
            for item in instance.items.all():
                success = InventoryItem.release_stock(
                    item.product_id,
                    item.quantity,
                    order_id=instance.order_id
                )
                if success:
                    logger.info(f"Released {item.quantity} units of {item.product.name} "
                                f"for order {instance.order_id}")
                else:
                    logger.error(f"Failed to release inventory for {item.product.name} "
                                 f"in order {instance.order_id}")

        elif instance.status == OrderStatus.DELIVERED:
            # Fulfill the order (reduce both reserved and total inventory)
            for item in instance.items.all():
                success = InventoryItem.fulfill_order(
                    item.product_id,
                    item.quantity,
                    order_id=instance.order_id
                )
                if success:
                    logger.info(f"Fulfilled {item.quantity} units of {item.product.name} "
                                f"for order {instance.order_id}")
                else:
                    logger.error(f"Failed to fulfill inventory for {item.product.name} "
                                 f"in order {instance.order_id}")


@receiver(post_save, sender=OrderItem)
def order_item_created(sender, instance, created, **kwargs):
    """Handle order item creation"""
    if created:
        logger.info(f"Order item created: {instance.quantity} x {instance.product.name} "
                    f"for order {instance.order.order_id}")

        # Recalculate order total
        instance.order.calculate_total()


@receiver(post_delete, sender=OrderItem)
def order_item_deleted(sender, instance, **kwargs):
    """Handle order item deletion"""
    logger.info(f"Order item deleted: {instance.quantity} x {instance.product.name} "
                f"from order {instance.order.order_id}")

    # Recalculate order total
    instance.order.calculate_total()

    # If the order is still pending, release the reserved inventory
    if instance.order.status == OrderStatus.PENDING:
        InventoryItem.release_stock(
            instance.product_id,
            instance.quantity,
            order_id=instance.order.order_id
        )