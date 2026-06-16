from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Админ"
        MANAGER = "manager", "Менеджер"
        SENIOR_MANAGER = "senior_manager", "Старший менеджер"
        READER = "reader", "Читатель"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.READER,
        verbose_name="Роль"
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Привязанный склад",
    )

    timezone = models.CharField(
        max_length=50,
        default="Asia/Baku",
        verbose_name="Часовой пояс"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    def __str__(self):
        return self.username
