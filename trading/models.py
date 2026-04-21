from django.db import models
from django.conf import settings


class Trading(models.Model):
    class TradeType(models.TextChoices):
        SELL = "sell", "Продажа"
        PURCHASE = "purchase", "Покупка"

    trade_type = models.CharField(
        max_length=20,
        choices=TradeType.choices,
        verbose_name="Тип операции"
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="Товар"
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="Склад",
        null=True,          # 👈 ВАЖНО
        blank=True          # 👈 ВАЖНО
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="Пользователь"
    )

    quantity = models.PositiveIntegerField(verbose_name="Количество")

    quantity_before = models.IntegerField(
        default=0,
        verbose_name="Количество до"
    )

    quantity_after = models.IntegerField(
        default=0,
        verbose_name="Количество после"
    )

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "История склада"
        verbose_name_plural = "История склада"

    def __str__(self):
        return f"{self.get_trade_type_display()} | {self.product} | {self.warehouse} | {self.quantity}"