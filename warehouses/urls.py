from django.urls import path
from .views import warehouse_detail_view

app_name = "warehouses"

urlpatterns = [
    path("<uuid:pk>/", warehouse_detail_view, name="warehouse_detail"),
]