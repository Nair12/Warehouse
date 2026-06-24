from django.urls import path

from . import views

app_name = "shipments"

urlpatterns = [
    path("", views.shipment_task_list, name="shipment_task_list"),
    path("create/", views.shipment_task_create, name="shipment_task_create"),
    path("<int:pk>/", views.shipment_task_detail, name="shipment_task_detail"),
    path("<int:pk>/shipped/", views.shipment_task_mark_shipped, name="shipment_task_mark_shipped"),
    path("<int:pk>/problem/", views.shipment_task_mark_problem, name="shipment_task_mark_problem"),
]
