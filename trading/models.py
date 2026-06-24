from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Trading(models.Model):
    class TradeType(models.TextChoices):
        SELL = "sell", _("Продажа")
        PURCHASE = "purchase", _("Покупка")

    class Status(models.TextChoices):
        PENDING = "pending", _("В процессе")
        COMPLETED = "completed", _("Завершена")

    name = models.CharField(
        max_length=255,
        verbose_name=_("Название сделки")
    )

    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Комментарий")
    )

    trade_type = models.CharField(
        max_length=20,
        choices=TradeType.choices,
        verbose_name=_("Тип операции")
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус")
    )

    # Старое поле.
    # Оставляем для совместимости со старыми сделками,
    # но новые сделки должны использовать TradingItem.
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        related_name="trades",
        verbose_name=_("Товар"),
        null=True,
        blank=True
    )

    # Старое поле.
    # Оставляем для совместимости.
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.SET_NULL,
        related_name="trades",
        verbose_name=_("Склад"),
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name=_("Пользователь")
    )

    # Старое поле.
    # Основное количество теперь хранится в TradingItem.
    quantity = models.PositiveIntegerField(
        verbose_name=_("Количество"),
        default=0
    )

    quantity_before = models.IntegerField(
        default=0,
        verbose_name=_("Количество до")
    )

    quantity_after = models.IntegerField(
        default=0,
        verbose_name=_("Количество после")
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Время операции")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Создано")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Обновлено")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("История склада")
        verbose_name_plural = _("История склада")

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

        return _("Без товаров")

    @property
    def can_be_modified(self):
        if not self.created_at:
            return False

        limit_time = self.created_at + timedelta(hours=24)
        return timezone.now() <= limit_time

    @property
    def can_be_edited(self):
        return self.status == self.Status.PENDING

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
        verbose_name=_("Сделка")
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="trading_items",
        verbose_name=_("Товар")
    )

    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="trading_items",
        verbose_name=_("Склад")
    )

    # Сколько реально прошло по складу.
    # Для продажи — сколько уже отдали.
    # Для покупки — сколько уже получили.
    quantity = models.PositiveIntegerField(
        verbose_name=_("Количество"),
        default=0
    )

    # Сколько нужно было по сделке.
    requested_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Нужно")
    )

    # Сколько уже отдали / получили.
    fulfilled_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Отдали")
    )

    quantity_before = models.IntegerField(
        default=0,
        verbose_name=_("Количество до")
    )

    quantity_after = models.IntegerField(
        default=0,
        verbose_name=_("Количество после")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Создано")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Обновлено")
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
            "waiting": _("Ожидает"),
            "partial": _("Частично"),
            "done": _("Выполнено"),
        }

        return statuses.get(self.fulfillment_status, "—")

    class Meta:
        verbose_name = _("Позиция сделки")
        verbose_name_plural = _("Позиции сделки")

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
        return _("Файл для сделки #%(id)s") % {"id": self.trade.id}


class TradingAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", _("Создание")
        UPDATED = "updated", _("Редактирование")
        FULFILLED = "fulfilled", _("Дополнение")
        DELETED = "deleted", _("Удаление")
        ROLLBACK = "rollback", _("Откат склада")

    trading = models.ForeignKey(
        Trading,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name=_("Сделка"),
        null=True,
        blank=True
    )

    trading_id_snapshot = models.PositiveIntegerField(
        verbose_name=_("ID сделки"),
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="trading_audit_logs",
        verbose_name=_("Пользователь"),
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_("Действие")
    )

    description = models.TextField(
        verbose_name=_("Описание")
    )

    before_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Было")
    )

    after_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Стало")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Дата")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Аудит сделки")
        verbose_name_plural = _("Аудит сделок")

    def __str__(self):
        return _("%(action)s — сделка #%(id)s") % {
            "action": self.get_action_display(),
            "id": self.trading_id_snapshot or self.trading_id,
        }


class TradingComment(models.Model):
    trading = models.ForeignKey(
        Trading,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Сделка")
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trading_comments",
        verbose_name=_("Пользователь")
    )

    text = models.TextField(
        verbose_name=_("Комментарий")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Дата")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Обновлено")
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Комментарий")
        verbose_name_plural = _("Комментарии")

    @property
    def can_be_deleted_by_owner(self):
        return True

    def __str__(self):
        return _("Комментарий к сделке #%(id)s") % {"id": self.trading.id}
