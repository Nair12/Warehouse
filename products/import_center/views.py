from django.shortcuts import render
from users.decorators import role_required


@role_required(["admin"])
def import_center_home(request):
    """
    Главная страница Центра обработки Excel.
    Пока это стартовая страница. Позже сюда добавим:
    - загрузку Excel;
    - историю импортов;
    - анализ файлов;
    - проверку дублей;
    - подтверждение импорта.
    """
    return render(
        request,
        "import_center/home.html",
        {
            "title": "Центр обработки Excel",
        },
    )