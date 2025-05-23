from rest_framework import serializers
from .models import InventoryItem, InventoryTransaction


class InventoryItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    available_quantity = serializers.ReadOnlyField()
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'product_id', 'product_name', 'product_sku',
            'quantity', 'reserved_quantity', 'available_quantity',
            'minimum_threshold', 'maximum_capacity', 'is_low_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_is_low_stock(self, obj):
        return obj.available_quantity <= obj.minimum_threshold


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='inventory_item.product.name', read_only=True)
    product_sku = serializers.CharField(source='inventory_item.product.sku', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'transaction_id', 'product_name', 'product_sku',
            'transaction_type', 'quantity', 'previous_quantity', 'new_quantity',
            'previous_reserved', 'new_reserved', 'order_id', 'reference_number',
            'notes', 'processed_by', 'created_at'
        ]


class InventoryAdjustmentSerializer(serializers.Serializer):
    """Serializer for manual inventory adjustments"""
    adjustment_type = serializers.ChoiceField(
        choices=[('add', 'Add Stock'), ('remove', 'Remove Stock'), ('set', 'Set Quantity')]
    )
    quantity = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reference_number = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_quantity(self, value):
        adjustment_type = self.initial_data.get('adjustment_type')

        if adjustment_type == 'remove':
            # Check if we have enough stock to remove
            inventory_item = self.context['inventory_item']
            if value > inventory_item.quantity:
                raise serializers.ValidationError(
                    f"Cannot remove {value} units. Only {inventory_item.quantity} available."
                )

        return value