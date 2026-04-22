from django.urls import path
from .views import (
    test_view,
    users_manage_view,
    manager_dashboard,
    add_product_view,
    reader_dashboard,
    warehouse_create_view,
    warehouse_list_view,
    global_search,
)

urlpatterns = [
    path('test/', test_view, name='test_view'),

    path('users-manage/', users_manage_view, name='users_manage'),

    path('manager-dashboard/', manager_dashboard, name='manager_dashboard'),

    path('manager/product-add/', add_product_view, name='add_product_view'),

    path('reader-dashboard/', reader_dashboard, name='reader_dashboard'),

    path('manager/warehouse/add/', warehouse_create_view, name='add_warehouse_view'),

    path('manager/warehouses/', warehouse_list_view, name='warehouse_list'),

    path('search/', global_search, name='global_search'),
]