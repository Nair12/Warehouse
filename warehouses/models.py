import uuid
from django.db import models
from django.conf import settings


class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.city


class WarehouseTransfer(models.Model):
    STATUS_CHOICES = [
        ("completed", "Выполнено"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="warehouse_transfers",
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="outgoing_transfers",
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="incoming_transfers",
    )

    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="completed",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_warehouse_transfers",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name}: {self.from_warehouse.city} -> {self.to_warehouse.city} ({self.quantity} {self.product.get_unit_display()})"
