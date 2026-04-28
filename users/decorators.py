from functools import wraps
from django.http import HttpResponse
from django.shortcuts import redirect, render


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # если не вошёл → на логин
            if not request.user.is_authenticated:
                return redirect('/login/')

            # если роль не подходит
            if request.user.role not in allowed_roles:
                return render(
                    request,
                    "access_denied.html",
                    status=403
                )

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator