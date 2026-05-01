from django.urls import path
from .views import (
    product_list_view,
    product_create_view,
    product_detail_view,
    inventory_update_view,
    inventory_adjust_view,
    inventory_create_view,

    # 👇 новые
    warehouse_reader_detail_view,
    warehouse_reader_list_view,
)

app_name = "products"

urlpatterns = [
    # товары
    path("", product_list_view, name="product_list"),
    path("create/", product_create_view, name="product_create"),
    path("<uuid:pk>/", product_detail_view, name="product_detail"),

    # складские остатки
    path(
        "inventory/<uuid:pk>/edit/",
        inventory_update_view,
        name="inventory_edit"
    ),

    path(
        "<uuid:product_id>/warehouse/<uuid:warehouse_id>/add/",
        inventory_create_view,
        name="inventory_create"
    ),

    path(
        "inventory/<uuid:pk>/increase/",
        inventory_adjust_view,
        {"action": "increase"},
        name="inventory_increase"
    ),
    path(
        "inventory/<uuid:pk>/decrease/",
        inventory_adjust_view,
        {"action": "decrease"},
        name="inventory_decrease"
    ),

    # 🏬 СКЛАДЫ
    path("warehouses/", warehouse_reader_list_view, name="warehouse_reader_list"),
    path("warehouses/<uuid:pk>/", warehouse_reader_detail_view, name="warehouse_reader_detail"),
]