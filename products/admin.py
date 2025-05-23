from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Product


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'sku', 'price', 'is_active', 'stock_quantity', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'description', 'price', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def stock_quantity(self, obj):
        """Display current stock quantity"""
        if hasattr(obj, 'inventory'):
            return f"{obj.inventory.available_quantity} / {obj.inventory.quantity}"
        return "No inventory"

    stock_quantity.short_description = "Available / Total Stock"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('inventory')