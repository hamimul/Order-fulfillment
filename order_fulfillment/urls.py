from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from products.views import ProductViewSet
from orders.views import OrderViewSet, OrderBatchViewSet
from inventory.views import InventoryViewSet, InventoryTransactionViewSet
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# API Documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Order Fulfillment API",
        default_version='v1',
        description="""
        A scalable, production-grade backend system for distributed order fulfillment.
        
        ## Features
        - Product & Inventory Management
        - Asynchronous Order Processing
        - Bulk Order Operations
        - Automatic Stale Order Detection
        - Comprehensive Order History Tracking
        - Real-time Stock Management
        
        ## Authentication
        This demo API allows anonymous access. In production, implement proper authentication.
        """,
        contact=openapi.Contact(email="api@orderfulfilment.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# API Router
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-batches', OrderBatchViewSet, basename='orderbatch')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'inventory-transactions', InventoryTransactionViewSet, basename='inventorytransaction')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API
    path('api/v1/', include(router.urls)),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', 
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='api-root'),
    
    # Health check endpoint
    path('health/', include('core.urls')),
]