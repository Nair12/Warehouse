from django.contrib import admin
from .models import Product, Inventory


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "id")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product_name", "warehouse_city", "quantity")
    search_fields = ("product__name", "warehouse__city")
    list_filter = ("warehouse__city",)
    ordering = ("warehouse__city", "product__name")

    @admin.display(description="Товар", ordering="product__name")
    def product_name(self, obj):
        return obj.product.name

    @admin.display(description="Город", ordering="warehouse__city")
    def warehouse_city(self, obj):
        return obj.warehouse.city