from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    reserved_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'sku', 'is_active',
            'stock', 'available_stock', 'reserved_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_stock(self, obj):
        """Get total stock quantity"""
        if hasattr(obj, 'inventory'):
            return obj.inventory.quantity
        return 0

    def get_available_stock(self, obj):
        """Get available stock (total - reserved)"""
        if hasattr(obj, 'inventory'):
            return obj.inventory.available_quantity
        return 0

    def get_reserved_stock(self, obj):
        """Get reserved stock quantity"""
        if hasattr(obj, 'inventory'):
            return obj.inventory.reserved_quantity
        return 0


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    initial_stock = serializers.IntegerField(write_only=True, required=False, min_value=0)

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'sku', 'is_active', 'initial_stock']

    def create(self, validated_data):
        initial_stock = validated_data.pop('initial_stock', 0)
        product = super().create(validated_data)

        # Set initial stock if provided
        if initial_stock > 0 and hasattr(product, 'inventory'):
            product.inventory.quantity = initial_stock
            product.inventory.save()

        return product