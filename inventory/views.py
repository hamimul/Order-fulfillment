from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q, F
from .models import InventoryItem, InventoryTransaction
from .serializers import (
    InventoryItemSerializer, InventoryTransactionSerializer,
    InventoryAdjustmentSerializer
)


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related('product').all()
    serializer_class = InventoryItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product__is_active']
    search_fields = ['product__name', 'product__sku']
    ordering_fields = ['quantity', 'available_quantity', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter options
        low_stock = self.request.query_params.get('low_stock', None)
        out_of_stock = self.request.query_params.get('out_of_stock', None)

        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=F('minimum_threshold'))

        if out_of_stock == 'true':
            queryset = queryset.filter(Q(quantity=0) | Q(quantity__lte=F('reserved_quantity')))

        return queryset

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get transaction history for an inventory item"""
        inventory_item = self.get_object()
        transactions = InventoryTransaction.objects.filter(
            inventory_item=inventory_item
        ).order_by('-created_at')[:100]  # Last 100 transactions

        serializer = InventoryTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get version history for an inventory item"""
        inventory_item = self.get_object()
        history_records = inventory_item.history.all().order_by('-history_date')[:50]

        # Format the history records
        history_data = [{
            'changed_date': record.history_date,
            'quantity': record.quantity,
            'reserved_quantity': record.reserved_quantity,
            'changed_by': str(record.history_user) if record.history_user else 'System',
            'change_type': record.history_type
        } for record in history_records]

        return Response(history_data)

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """Manually adjust inventory quantity"""
        inventory_item = self.get_object()
        serializer = InventoryAdjustmentSerializer(
            data=request.data,
            context={'inventory_item': inventory_item}
        )

        if serializer.is_valid():
            adjustment_type = serializer.validated_data['adjustment_type']
            quantity = serializer.validated_data['quantity']
            notes = serializer.validated_data.get('notes', '')
            reference_number = serializer.validated_data.get('reference_number', '')

            with transaction.atomic():
                previous_quantity = inventory_item.quantity

                if adjustment_type == 'add':
                    new_quantity = previous_quantity + quantity
                elif adjustment_type == 'remove':
                    new_quantity = max(0, previous_quantity - quantity)
                else:  # set
                    new_quantity = quantity

                # Update inventory
                inventory_item.quantity = new_quantity
                inventory_item.save()

                # Create transaction record
                InventoryTransaction.objects.create(
                    inventory_item=inventory_item,
                    transaction_type=InventoryTransaction.ADJUST,
                    quantity=abs(new_quantity - previous_quantity),
                    previous_quantity=previous_quantity,
                    new_quantity=new_quantity,
                    previous_reserved=inventory_item.reserved_quantity,
                    new_reserved=inventory_item.reserved_quantity,
                    reference_number=reference_number,
                    notes=notes or f"Manual {adjustment_type} adjustment",
                    processed_by=getattr(request.user, 'username', 'api_user')
                )

            return Response({
                'success': True,
                'previous_quantity': previous_quantity,
                'new_quantity': new_quantity,
                'adjustment': new_quantity - previous_quantity
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Get all items with low stock"""
        low_stock_items = self.queryset.filter(
            quantity__lte=F('minimum_threshold')
        ).order_by('quantity')

        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get inventory summary statistics"""
        total_items = self.queryset.count()
        low_stock_count = self.queryset.filter(quantity__lte=F('minimum_threshold')).count()
        out_of_stock_count = self.queryset.filter(quantity=0).count()

        summary = {
            'total_items': total_items,
            'low_stock_items': low_stock_count,
            'out_of_stock_items': out_of_stock_count,
            'healthy_stock_items': total_items - low_stock_count - out_of_stock_count
        }

        return Response(summary)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryTransaction.objects.select_related('inventory_item__product').all()
    serializer_class = InventoryTransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'order_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']