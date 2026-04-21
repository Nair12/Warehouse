from django.urls import path
from .views import (
    product_list_view,
    product_create_view,
    product_detail_view,
    inventory_update_view,
    inventory_adjust_view,
    inventory_create_view,
)

app_name = "products"

urlpatterns = [
    path("", product_list_view, name="product_list"),
    path("create/", product_create_view, name="product_create"),
    path("<uuid:pk>/", product_detail_view, name="product_detail"),

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

    # старые + / - можешь оставить (они не мешают)
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
]