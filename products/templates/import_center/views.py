from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def import_center_home(request):
    """
    Главная страница центра импорта.

    Пока здесь только простой экран выбора сценария.
    Логику импорта подключим следующим шагом.
    """
    return render(request, "products/import_center/home.html")
