from django.urls import path
from . import views

urlpatterns = [
    path('', views.trading_list, name='trading_list'),
    path('create/', views.trading_create, name='trading_create'),
    path('history/', views.admin_trading_history, name='admin_trading_history'),
    path('<int:pk>/', views.trading_detail, name='trading_detail'),
    path('<int:pk>/edit/', views.trading_update, name='trading_update'),

    # 🔥 НОВЫЙ URL ДЛЯ ОСТАТКА
    path('get-stock/', views.get_stock, name='get_stock'),
]