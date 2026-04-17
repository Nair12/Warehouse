from django.urls import path
from .views import product_list_view, product_create_view, product_detail_view

urlpatterns = [
    path("", product_list_view, name="product_list"),
    path("create/", product_create_view, name="product_create"),
    path("<int:pk>/", product_detail_view, name="product_detail"),
]