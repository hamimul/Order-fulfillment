from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import random
import time
import logging
from .models import Order, OrderStatus
from inventory.models import InventoryItem

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_order(self, order_id):
    """Process an order through its lifecycle asynchronously"""
    try:
        order = Order.objects.get(order_id=order_id)
        logger.info(f"Starting to process order {order_id}")

        # Ensure order is in pending state
        if order.status != OrderStatus.PENDING:
            logger.warning(f"Order {order_id} is not in pending state, current status: {order.status}")
            return False

        # Move to processing
        order.update_status(OrderStatus.PROCESSING, "Started async processing")
        logger.info(f"Order {order_id} moved to processing")

        # Simulate processing delay (2-5 seconds)
        processing_time = random.uniform(2, 5)
        time.sleep(processing_time)

        # 10% chance of processing failure
        if random.random() < 0.1:
            order.update_status(OrderStatus.FAILED, "Processing failed - random failure simulation")
            logger.warning(f"Order {order_id} failed during processing")
            return False

        # Move to shipped
        order.update_status(OrderStatus.SHIPPED, "Order shipped successfully")
        logger.info(f"Order {order_id} shipped")

        # Simulate shipping delay (3-8 seconds)
        shipping_time = random.uniform(3, 8)
        time.sleep(shipping_time)

        # 5% chance of shipping failure
        if random.random() < 0.05:
            order.update_status(OrderStatus.FAILED, "Shipping failed - random failure simulation")
            logger.warning(f"Order {order_id} failed during shipping")
            return False

        # Move to delivered
        order.update_status(OrderStatus.DELIVERED, "Order delivered successfully")
        logger.info(f"Order {order_id} delivered successfully")

        return True

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        return False
    except Exception as exc:
        logger.error(f"Error processing order {order_id}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_stale_orders():
    """Identify and handle stale orders"""
    logger.info("Starting stale order check")

    # Define time thresholds for each status
    thresholds = {
        OrderStatus.PENDING: timedelta(minutes=5),  # 5 minutes for demo
        OrderStatus.PROCESSING: timedelta(minutes=10),  # 10 minutes for demo
        OrderStatus.SHIPPED: timedelta(hours=1),  # 1 hour for demo
    }

    stale_orders_handled = 0

    for status, threshold in thresholds.items():
        time_threshold = timezone.now() - threshold

        # Find stale orders
        stale_orders = Order.objects.filter(
            status=status,
            current_state_since__lt=time_threshold
        )

        for order in stale_orders:
            logger.warning(f"Found stale order: {order.order_id} in status {status}")

            if status == OrderStatus.PENDING:
                # Restart processing for pending orders
                order.update_status(OrderStatus.PENDING, "Restarted due to stale state")
                process_order.delay(str(order.order_id))
                logger.info(f"Restarted processing for stale pending order: {order.order_id}")

            elif status == OrderStatus.PROCESSING:
                # 70% chance to retry, 30% chance to cancel
                if random.random() < 0.7:
                    order.update_status(OrderStatus.PENDING, "Retrying due to stale processing state")
                    process_order.delay(str(order.order_id))
                    logger.info(f"Retrying stale processing order: {order.order_id}")
                else:
                    order.update_status(OrderStatus.CANCELLED, "Cancelled due to prolonged processing")
                    logger.info(f"Cancelled stale processing order: {order.order_id}")

            elif status == OrderStatus.SHIPPED:
                # Assume delivered if shipped for too long
                order.update_status(OrderStatus.DELIVERED, "Auto-delivered due to prolonged shipping")
                logger.info(f"Auto-delivered stale shipped order: {order.order_id}")

            stale_orders_handled += 1

    logger.info(f"Stale order check completed. Handled {stale_orders_handled} stale orders")
    return f"Processed {stale_orders_handled} stale orders"


@shared_task
def generate_daily_report():
    """Generate daily order processing report"""
    today = timezone.now().date()
    today_start = timezone.datetime.combine(today, timezone.datetime.min.time())
    today_start = timezone.make_aware(today_start)

    # Get today's order statistics
    orders_today = Order.objects.filter(created_at__gte=today_start)

    stats = {
        'total_orders': orders_today.count(),
        'pending': orders_today.filter(status=OrderStatus.PENDING).count(),
        'processing': orders_today.filter(status=OrderStatus.PROCESSING).count(),
        'shipped': orders_today.filter(status=OrderStatus.SHIPPED).count(),
        'delivered': orders_today.filter(status=OrderStatus.DELIVERED).count(),
        'cancelled': orders_today.filter(status=OrderStatus.CANCELLED).count(),
        'failed': orders_today.filter(status=OrderStatus.FAILED).count(),
    }

    logger.info(f"Daily report for {today}: {stats}")
    return stats


@shared_task
def cleanup_old_order_history():
    """Clean up old order history records (older than 90 days)"""
    from .models import OrderStatusHistory

    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_count, _ = OrderStatusHistory.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    logger.info(f"Cleaned up {deleted_count} old order history records")
    return f"Deleted {deleted_count} old history records"