from django.db import models
from core.models import BaseModel


class Product(BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"