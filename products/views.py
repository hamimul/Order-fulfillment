from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F
from .models import Product
from .serializers import ProductSerializer, ProductCreateUpdateSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('inventory').filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'sku', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductSerializer

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        low_stock_products = self.queryset.filter(
            inventory__quantity__lte=F('inventory__minimum_threshold')
        )
        serializer = self.get_serializer(low_stock_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get products that are out of stock"""
        out_of_stock_products = self.queryset.filter(
            Q(inventory__quantity=0) | Q(inventory__available_quantity=0)
        )
        serializer = self.get_serializer(out_of_stock_products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stock_history(self, request, pk=None):
        """Get stock history for a specific product"""
        product = self.get_object()
        if hasattr(product, 'inventory'):
            transactions = product.inventory.transactions.all()[:50]  # Last 50 transactions
            from inventory.serializers import InventoryTransactionSerializer
            serializer = InventoryTransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        return Response([])