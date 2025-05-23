from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from .models import Order, OrderStatus, OrderBatch
from .serializers import (
    OrderCreateSerializer, OrderDetailSerializer, OrderListSerializer,
    BulkOrderCreateSerializer
)
from .tasks import check_stale_orders
import logging

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product', 'status_history').all()
    lookup_field = 'order_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'customer_email']
    search_fields = ['order_id', 'customer_name', 'customer_email']
    ordering_fields = ['created_at', 'updated_at', 'total_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter options
        stale_only = self.request.query_params.get('stale_only', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)

        if stale_only == 'true':
            # Get stale orders based on our business logic
            stale_orders = []
            for order in queryset:
                if order.is_stale:
                    stale_orders.append(order.id)
            queryset = queryset.filter(id__in=stale_orders)

        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset

    def create(self, request, *args, **kwargs):
        """Create a single order"""
        logger.info(f"Creating new order for customer: {request.data.get('customer_email')}")

        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            order = serializer.save()

            logger.info(f"Successfully created order: {order.order_id}")
            headers = self.get_success_headers(serializer.data)

            return Response(
                OrderDetailSerializer(order).data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Handle bulk order creation"""
        logger.info(f"Processing bulk order creation for {len(request.data.get('orders', []))} orders")

        serializer = BulkOrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                result = serializer.save()

                order_ids = [str(order.order_id) for order in result['created_orders']]
                logger.info(f"Successfully created {len(order_ids)} orders in bulk")

                return Response({
                    'batch_id': str(result['batch_id']),
                    'order_ids': order_ids,
                    'total_orders': result['total_orders'],
                    'status': 'success'
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Bulk order creation failed: {str(e)}")
                return Response({
                    'error': 'Bulk order creation failed',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, order_id=None):
        """Cancel an order"""
        order = self.get_object()

        if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            return Response({
                'error': f'Cannot cancel order in {order.status} status'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.update_status(OrderStatus.CANCELLED, "Cancelled via API request")
        logger.info(f"Order {order.order_id} cancelled via API")

        return Response({
            'success': True,
            'message': f'Order {order.order_id} has been cancelled',
            'new_status': order.status
        })

    @action(detail=True, methods=['get'])
    def history(self, request, order_id=None):
        """Get detailed version history of an order"""
        order = self.get_object()
        history_records = order.history.all().order_by('-history_date')

        # Format data for response
        history_data = [{
            'changed_date': record.history_date,
            'status': record.status,
            'version': record.version,
            'customer_name': record.customer_name,
            'customer_email': record.customer_email,
            'total_amount': str(record.total_amount),
            'changed_by': str(record.history_user) if record.history_user else 'System',
            'change_type': record.history_type
        } for record in history_records]

        return Response(history_data)

    @action(detail=False, methods=['post'])
    def check_stale(self, request):
        """Manually trigger stale order check"""
        logger.info("Manual stale order check triggered via API")
        check_stale_orders.delay()
        return Response({
            'status': 'success',
            'message': 'Stale order check has been queued for processing'
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get order statistics"""
        total_orders = self.queryset.count()

        status_counts = self.queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        # Convert to dict for easier consumption
        status_breakdown = {item['status']: item['count'] for item in status_counts}

        # Calculate stale orders
        stale_count = sum(1 for order in self.queryset if order.is_stale)

        # Recent orders (last 24 hours)
        recent_threshold = timezone.now() - timezone.timedelta(hours=24)
        recent_orders = self.queryset.filter(created_at__gte=recent_threshold).count()

        return Response({
            'total_orders': total_orders,
            'status_breakdown': status_breakdown,
            'stale_orders': stale_count,
            'recent_orders_24h': recent_orders,
            'completion_rate': round(
                (status_breakdown.get('delivered', 0) / max(total_orders, 1)) * 100, 2
            )
        })

    @action(detail=False, methods=['get'])
    def search_by_customer(self, request):
        """Search orders by customer email or name"""
        customer_query = request.query_params.get('q', '').strip()

        if not customer_query:
            return Response({
                'error': 'Please provide a search query parameter "q"'
            }, status=status.HTTP_400_BAD_REQUEST)

        orders = self.queryset.filter(
            Q(customer_email__icontains=customer_query) |
            Q(customer_name__icontains=customer_query)
        )

        serializer = OrderListSerializer(orders, many=True)
        return Response({
            'count': orders.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['get'])
    def tracking(self, request, order_id=None):
        """Get order tracking information"""
        order = self.get_object()

        # Generate tracking timeline
        timeline = []
        for history in order.status_history.all().order_by('created_at'):
            timeline.append({
                'status': history.to_status,
                'timestamp': history.created_at,
                'notes': history.notes,
                'processed_by': history.processed_by
            })

        return Response({
            'order_id': str(order.order_id),
            'current_status': order.status,
            'tracking_number': order.tracking_number,
            'timeline': timeline,
            'estimated_delivery': None,  # Could be calculated based on shipping method
            'customer_info': {
                'name': order.customer_name,
                'email': order.customer_email
            }
        })


class OrderBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderBatch.objects.all()
    lookup_field = 'batch_id'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        # We'll create a simple serializer inline
        from rest_framework import serializers

        class OrderBatchSerializer(serializers.ModelSerializer):
            success_rate = serializers.SerializerMethodField()

            class Meta:
                model = OrderBatch
                fields = '__all__'

            def get_success_rate(self, obj):
                if obj.total_orders > 0:
                    return round((obj.successful_orders / obj.total_orders) * 100, 2)
                return 0

        return OrderBatchSerializer