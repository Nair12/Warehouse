from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from products.models import Product


class ShipmentTask(models.Model):
    STATUS_NEW = "new"
    STATUS_SEEN = "seen"
    STATUS_SHIPPED = "shipped"
    STATUS_PROBLEM = "problem"

    STATUS_CHOICES = [
        (STATUS_NEW, _("Новое")),
        (STATUS_SEEN, _("Увидел")),
        (STATUS_SHIPPED, _("Отправлено")),
        (STATUS_PROBLEM, _("Проблема")),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_shipment_tasks",
        verbose_name=_("Кто создал"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_shipment_tasks",
        verbose_name=_("Кому поручено"),
    )

    recipient_name = models.CharField(
        max_length=255,
        verbose_name=_("Кому отправить"),
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_("Комментарий"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        verbose_name=_("Статус"),
    )

    seen_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Когда увидел"),
    )
    shipped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Когда отправлено"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Дата создания"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Дата обновления"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Задание на отправку")
        verbose_name_plural = _("Задания на отправку")

    def __str__(self):
        return f"{self.recipient_name}"

    def mark_seen(self):
        if self.status == self.STATUS_NEW:
            self.status = self.STATUS_SEEN
            self.seen_at = timezone.now()
            self.save(update_fields=["status", "seen_at", "updated_at"])

    def mark_shipped(self):
        self.status = self.STATUS_SHIPPED
        self.shipped_at = timezone.now()
        self.save(update_fields=["status", "shipped_at", "updated_at"])

    def mark_problem(self):
        self.status = self.STATUS_PROBLEM
        self.save(update_fields=["status", "updated_at"])


class ShipmentTaskItem(models.Model):
    task = models.ForeignKey(
        ShipmentTask,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Задание"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="shipment_task_items",
        verbose_name=_("Товар"),
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Количество"),
    )

    class Meta:
        verbose_name = _("Товар в задании на отправку")
        verbose_name_plural = _("Товары в задании на отправку")

    def __str__(self):
        return f"{self.quantity} x {self.product}"
