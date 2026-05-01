from django.urls import path
from . import views


urlpatterns = [
    path('', views.trading_list, name='trading_list'),
    path('orders/', views.orders_list, name='orders_list'),
    path('create/', views.trading_create, name='trading_create'),
    path('history/', views.admin_trading_history, name='admin_trading_history'),

    path('<int:pk>/', views.trading_detail, name='trading_detail'),
    path('<int:pk>/fulfill/', views.trading_fulfill, name='trading_fulfill'),
    path('<int:pk>/edit/', views.trading_update, name='trading_update'),

    # 🔥 удаление сделки
    path('<int:pk>/delete/', views.trading_delete, name='trading_delete'),

    # 🔥 удаление комментария
    path('<int:pk>/comments/<int:comment_id>/delete/', views.trading_comment_delete, name='trading_comment_delete'),

    path('get-stock/', views.get_stock, name='get_stock'),
]
