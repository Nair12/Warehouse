from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone

class Trading(models.Model):
    class TradeType(models.TextChoices):
        SELL = "sell", "Продажа"
        PURCHASE = "purchase", "Покупка"

    name = models.CharField(
        max_length=255,
        verbose_name="Название сделки"
    )

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

    # Старое поле.
    # Оставляем для совместимости со старыми сделками,
    # но новые сделки должны использовать TradingItem.
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        related_name="trades",
        verbose_name="Товар",
        null=True,
        blank=True
    )

    # Старое поле.
    # Оставляем для совместимости.
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.SET_NULL,
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

    # Старое поле.
    # Основное количество теперь хранится в TradingItem.
    quantity = models.PositiveIntegerField(
        verbose_name="Количество",
        default=0
    )

    quantity_before = models.IntegerField(
        default=0,
        verbose_name="Количество до"
    )

    quantity_after = models.IntegerField(
        default=0,
        verbose_name="Количество после"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время операции"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "История склада"
        verbose_name_plural = "История склада"

    @property
    def title(self):
        return self.name

    @property
    def total_quantity(self):
        items_total = self.items.aggregate(
            total=models.Sum("quantity")
        )["total"]

        return items_total or self.quantity or 0

    @property
    def products_display(self):
        items = self.items.select_related("product").all()

        if items.exists():
            return ", ".join(
                item.product.name for item in items if item.product
            )

        if self.product:
            return self.product.name

        return "Без товаров"

    @property
    def can_be_modified(self):
        if not self.created_at:
            return False

        limit_time = self.created_at + timedelta(hours=24)
        return timezone.now() <= limit_time

    @property
    def edit_deadline(self):
        if not self.created_at:
            return None

        return self.created_at + timedelta(hours=24)

    def __str__(self):
        return self.name


class TradingItem(models.Model):
    trading = models.ForeignKey(
        Trading,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Сделка"
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="trading_items",
        verbose_name="Товар"
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="trading_items",
        verbose_name="Склад"
    )

    # Сколько реально прошло по складу.
    # Для продажи — сколько уже отдали.
    # Для покупки — сколько уже получили.
    quantity = models.PositiveIntegerField(
        verbose_name="Количество"
    )

    # Сколько нужно было по сделке.
    requested_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Нужно"
    )

    # Сколько уже отдали / получили.
    fulfilled_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="Отдали"
    )

    quantity_before = models.IntegerField(
        default=0,
        verbose_name="Количество до"
    )

    quantity_after = models.IntegerField(
        default=0,
        verbose_name="Количество после"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено"
    )

    @property
    def remaining_quantity(self):
        remaining = self.requested_quantity - self.fulfilled_quantity
        return max(remaining, 0)

    @property
    def fulfillment_status(self):
        if self.fulfilled_quantity <= 0:
            return "waiting"

        if self.remaining_quantity > 0:
            return "partial"

        return "done"

    @property
    def fulfillment_status_display(self):
        statuses = {
            "waiting": "Ожидает",
            "partial": "Частично",
            "done": "Выполнено",
        }

        return statuses.get(self.fulfillment_status, "—")

    class Meta:
        verbose_name = "Позиция сделки"
        verbose_name_plural = "Позиции сделки"

    def __str__(self):
        return (
            f"{self.trading.name} — "
            f"{self.product} — "
            f"{self.warehouse} "
            f"({self.quantity})"
        )


class TradingAttachment(models.Model):
    trade = models.ForeignKey(
        Trading,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    file = models.FileField(
        upload_to="trades/attachments/%Y/%m/%d/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Файл для сделки #{self.trade.id}"