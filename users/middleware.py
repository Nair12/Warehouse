import pytz
from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Если пользователь авторизован и у него есть timezone
        if request.user.is_authenticated:
            user_tz = getattr(request.user, "timezone", None)

            if user_tz:
                try:
                    timezone.activate(pytz.timezone(user_tz))
                except Exception:
                    timezone.deactivate()
            else:
                timezone.deactivate()

        else:
            timezone.deactivate()

        return self.get_response(request)
