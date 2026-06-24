# shipments/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ShipmentTask, ShipmentTaskItem


class ShipmentTaskItemInline(admin.TabularInline):
    model = ShipmentTaskItem
    extra = 1
    fields = ("product", "quantity")


@admin.register(ShipmentTask)
class ShipmentTaskAdmin(admin.ModelAdmin):
    list_display = (
        "recipient_name",
        "assigned_to",
        "created_by",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "recipient_name",
        "comment",
        "created_by__username",
        "assigned_to__username",
    )

    readonly_fields = (
        "seen_at",
        "shipped_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (_("Основное"), {
            "fields": (
                "created_by",
                "assigned_to",
                "status",
            )
        }),
        (_("Задание"), {
            "fields": (
                "recipient_name",
                "comment",
            )
        }),
        (_("Даты"), {
            "fields": (
                "seen_at",
                "shipped_at",
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [ShipmentTaskItemInline]


@admin.register(ShipmentTaskItem)
class ShipmentTaskItemAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "product",
        "quantity",
    )

    search_fields = (
        "task__recipient_name",
        "product__name",
        "product__description",
    )