from django.urls import path
from .views import test_view, manager_dashboard, reader_dashboard, users_manage_view, add_product_view
from .views import manager_dashboard, reader_dashboard

urlpatterns = [
    path('test/', test_view),
    path('users-manage/', users_manage_view),
    path('manager-dashboard/', manager_dashboard, name='manager_dashboard'),
    path('manager/product-add/', add_product_view, name='add_product_view'),
    path('reader-dashboard/', reader_dashboard, name='reader_dashboard'),
    
]