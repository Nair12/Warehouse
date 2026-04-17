from django.urls import path
from .views import test_view, manager_dashboard, reader_dashboard, users_manage_view, add_product_view, \
    warehouse_create_view, warehouse_list_view
from .views import manager_dashboard, reader_dashboard
from .views import test_view, manager_dashboard, reader_dashboard, users_manage_view, add_product_view

urlpatterns = [
    path('test/', test_view),


    path('users-manage/', users_manage_view),
    path('manager-dashboard/', manager_dashboard, name='manager_dashboard'),
    path('manager/product-add/', add_product_view, name='add_product_view'),
    path('reader-dashboard/', reader_dashboard, name='reader_dashboard'),
    path('manager/warehouse/add', warehouse_create_view, name='add_wsarehouse_view'),
path('manger/warehouses/', warehouse_list_view, name='warehouse_list'),


]