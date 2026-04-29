import uuid
from django.db import models
from django.utils import timezone


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

    def save(self, *args, **kwargs):
        old_price = None
        is_new = self.pk is None

        if self.pk:
            old_product = Product.objects.filter(pk=self.pk).first()
            if old_product:
                old_price = old_product.price

        super().save(*args, **kwargs)

        if is_new:
            ProductPriceHistory.objects.get_or_create(
                product=self,
                price=self.price,
                change_type=ProductPriceHistory.CHANGE_TYPE_INITIAL,
                defaults={
                    "created_at": self.created_at,
                },
            )
        elif old_price != self.price:
            ProductPriceHistory.objects.create(
                product=self,
                price=self.price,
                change_type=ProductPriceHistory.CHANGE_TYPE_UPDATE,
            )

    def __str__(self):
        return self.name


class ProductPriceHistory(models.Model):
    CHANGE_TYPE_INITIAL = "initial"
    CHANGE_TYPE_UPDATE = "update"

    CHANGE_TYPE_CHOICES = (
        (CHANGE_TYPE_INITIAL, "Цена при создании"),
        (CHANGE_TYPE_UPDATE, "Обновление цены"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="price_history",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default=CHANGE_TYPE_UPDATE,
        verbose_name="Тип изменения",
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.price}"


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
