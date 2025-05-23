from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin
from .models import Order, OrderItem, OrderStatusHistory, OrderBatch


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price', 'total_price']

    def total_price(self, obj):
        if obj.id:
            return f"${obj.total_price:.2f}"
        return "-"

    total_price.short_description = "Total"


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['from_status', 'to_status', 'notes', 'processed_by', 'created_at']
    ordering = ['-created_at']


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):
    list_display = [
        'order_id', 'customer_name', 'customer_email', 'status_display',
        'total_amount', 'priority', 'items_count', 'created_at'
    ]
    list_filter = ['status', 'priority', 'created_at', 'updated_at']
    search_fields = ['order_id', 'customer_name', 'customer_email']
    ordering = ['-created_at']
    readonly_fields = [
        'order_id', 'version', 'current_state_since', 'processing_started_at',
        'completed_at', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'status', 'priority', 'version')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email')
        }),
        ('Financial Information', {
            'fields': ('total_amount', 'payment_method')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'current_state_since', 'processing_started_at', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [OrderItemInline, OrderStatusHistoryInline]

    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#ffc107',  # Yellow
            'processing': '#17a2b8',  # Blue
            'shipped': '#6f42c1',  # Purple
            'delivered': '#28a745',  # Green
            'cancelled': '#6c757d',  # Gray
            'failed': '#dc3545',  # Red
        }
        color = colors.get(obj.status, '#000000')

        style = f"color: {color}; font-weight: bold; text-transform: uppercase;"
        return format_html(f'<span style="{style}">{obj.get_status_display()}</span>')

    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Items"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

    actions = ['cancel_orders', 'mark_as_processing']

    def cancel_orders(self, request, queryset):
        """Bulk cancel orders"""
        cancelled_count = 0
        for order in queryset:
            if order.status in ['pending', 'processing']:
                order.update_status('cancelled', 'Cancelled via admin action')
                cancelled_count += 1

        self.message_user(request, f"Successfully cancelled {cancelled_count} orders.")

    cancel_orders.short_description = "Cancel selected orders"

    def mark_as_processing(self, request, queryset):
        """Bulk mark orders as processing"""
        updated_count = 0
        for order in queryset:
            if order.status == 'pending':
                order.update_status('processing', 'Marked as processing via admin action')
                updated_count += 1

        self.message_user(request, f"Successfully marked {updated_count} orders as processing.")

    mark_as_processing.short_description = "Mark as processing"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'product_name', 'quantity', 'price', 'total_price', 'order_status']
    list_filter = ['order__status', 'created_at']
    search_fields = ['order__order_id', 'product__name', 'product__sku']
    ordering = ['-created_at']
    readonly_fields = ['order', 'product', 'quantity', 'price', 'total_price', 'created_at', 'updated_at']

    def order_id(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_id)

    order_id.short_description = "Order ID"
    order_id.admin_order_field = 'order__order_id'

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = "Product"
    product_name.admin_order_field = 'product__name'

    def order_status(self, obj):
        return obj.order.get_status_display()

    order_status.short_description = "Order Status"
    order_status.admin_order_field = 'order__status'

    def total_price(self, obj):
        return f"${obj.total_price:.2f}"

    total_price.short_description = "Total"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'product')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'from_status', 'to_status', 'processed_by', 'created_at']
    list_filter = ['from_status', 'to_status', 'created_at', 'processed_by']
    search_fields = ['order__order_id']
    ordering = ['-created_at']
    readonly_fields = ['order', 'from_status', 'to_status', 'notes', 'processed_by', 'created_at']

    def order_id(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_id)

    order_id.short_description = "Order ID"
    order_id.admin_order_field = 'order__order_id'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')


@admin.register(OrderBatch)
class OrderBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'total_orders', 'successful_orders', 'failed_orders', 'success_rate', 'status',
                    'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['batch_id']
    ordering = ['-created_at']
    readonly_fields = ['batch_id', 'total_orders', 'successful_orders', 'failed_orders', 'success_rate', 'created_at',
                       'updated_at']

    def success_rate(self, obj):
        if obj.total_orders > 0:
            rate = (obj.successful_orders / obj.total_orders) * 100
            return f"{rate:.1f}%"
        return "0%"

    success_rate.short_description = "Success Rate"