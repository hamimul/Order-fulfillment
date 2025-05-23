from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import InventoryItem, InventoryTransaction


@admin.register(InventoryItem)
class InventoryItemAdmin(SimpleHistoryAdmin):
    list_display = [
        'product_name', 'product_sku', 'quantity', 'reserved_quantity',
        'available_quantity_display', 'stock_status', 'updated_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['product__name', 'product__sku']
    ordering = ['product__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Product Information', {
            'fields': ('product',)
        }),
        ('Inventory Levels', {
            'fields': ('quantity', 'reserved_quantity', 'minimum_threshold', 'maximum_capacity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = "Product"
    product_name.admin_order_field = 'product__name'

    def product_sku(self, obj):
        return obj.product.sku

    product_sku.short_description = "SKU"
    product_sku.admin_order_field = 'product__sku'

    def available_quantity_display(self, obj):
        return obj.available_quantity

    available_quantity_display.short_description = "Available"

    def stock_status(self, obj):
        """Display stock status with color coding"""
        available = obj.available_quantity
        threshold = obj.minimum_threshold

        if available == 0:
            return format_html('<span style="color: red; font-weight: bold;">OUT OF STOCK</span>')
        elif available <= threshold:
            return format_html('<span style="color: orange; font-weight: bold;">LOW STOCK</span>')
        else:
            return format_html('<span style="color: green;">GOOD</span>')

    stock_status.short_description = "Status"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'product_name', 'transaction_type', 'quantity',
        'new_quantity', 'order_id', 'processed_by', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at', 'processed_by']
    search_fields = ['transaction_id', 'inventory_item__product__name', 'order_id', 'reference_number']
    ordering = ['-created_at']
    readonly_fields = [
        'transaction_id', 'inventory_item', 'transaction_type', 'quantity',
        'previous_quantity', 'new_quantity', 'previous_reserved', 'new_reserved',
        'order_id', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'inventory_item', 'transaction_type', 'order_id')
        }),
        ('Quantity Changes', {
            'fields': (
                'quantity',
                ('previous_quantity', 'new_quantity'),
                ('previous_reserved', 'new_reserved')
            )
        }),
        ('Additional Information', {
            'fields': ('reference_number', 'notes', 'processed_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_name(self, obj):
        return obj.inventory_item.product.name

    product_name.short_description = "Product"
    product_name.admin_order_field = 'inventory_item__product__name'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('inventory_item__product')

    def has_add_permission(self, request):
        # Transactions should only be created through the system
        return False

    def has_change_permission(self, request, obj=None):
        # Transactions should be immutable
        return False