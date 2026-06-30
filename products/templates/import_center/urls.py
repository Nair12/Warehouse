from django.urls import path

from .views import import_center_home

app_name = "import_center"

urlpatterns = [
    path("", import_center_home, name="home"),
]