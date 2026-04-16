from functools import wraps
from django.http import HttpResponse
from django.shortcuts import redirect


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # если не вошёл → на логин
            if not request.user.is_authenticated:
                return redirect('/login/')

            # если роль не подходит
            if request.user.role not in allowed_roles:
                return HttpResponse("У тебя нет доступа")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator