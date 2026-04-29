import uuid
from django.db import models


class Product(models.Model):
    UNIT_PIECE = "pcs"
    UNIT_KG = "kg"

    UNIT_CHOICES = (
        (UNIT_PIECE, "шт"),
        (UNIT_KG, "кг"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    picture = models.ImageField(upload_to="products/", blank=True, null=True)
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default=UNIT_PIECE,
        verbose_name="Единица измерения",
    )
    user_id = models.UUIDField(blank=True, null=True)

    warehouses = models.ManyToManyField(
        "warehouses.Warehouse",
        through="products.Inventory",
        related_name="products",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    quantity = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse",
            )
        ]

    def __str__(self):
        return f"{self.product} @ {self.warehouse}: {self.quantity} {self.product.get_unit_display()}"
