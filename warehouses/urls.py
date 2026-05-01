# warehouses/urls.py

from django.urls import path
from .views import (
    warehouse_detail_view,
    warehouse_transfer_create_view,
    warehouse_transfer_history_view,
    warehouse_inventory_quantity_api,
)

app_name = "warehouses"

urlpatterns = [
    path("<uuid:pk>/", warehouse_detail_view, name="warehouse_detail"),
    path("transfer/create/", warehouse_transfer_create_view, name="warehouse_transfer_create"),
    path("transfer/history/", warehouse_transfer_history_view, name="warehouse_transfer_history"),
    path("api/inventory-quantity/", warehouse_inventory_quantity_api, name="inventory_quantity_api"),
]