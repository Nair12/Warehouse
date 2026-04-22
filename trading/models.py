from django.db import models
from django.conf import settings


class Trading(models.Model):
    class TradeType(models.TextChoices):
        SELL = "sell", "Продажа"
        PURCHASE = "purchase", "Покупка"

    # 👇 НОВОЕ ПОЛЕ — название сделки
    name = models.CharField(
        max_length=255,
        verbose_name="Название сделки"
    )

    # 👇 НОВОЕ ПОЛЕ — комментарий (необязательный)
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарий"
    )

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
        null=True,
        blank=True
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

    @property
    def title(self):
        return self.name

    def __str__(self):
        return self.name