from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # 1. Добавляем 'warehouse' в колонки таблицы списка пользователей
    list_display = (
        'id',
        'username',
        'email',
        'role',
        'warehouse',
        'is_staff',
        'is_superuser',
        'last_login',
    )


    list_filter = ('role', 'warehouse', 'is_staff', 'is_superuser')


    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {
            'fields': (
                'role',
                'warehouse',
                'created_at',
                'updated_at'
            )
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'last_login')