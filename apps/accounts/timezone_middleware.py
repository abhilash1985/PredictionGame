import zoneinfo

from django.utils import timezone


class UserTimezoneMiddleware:
    """Activate profile timezone, else django_timezone cookie, else UTC."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = self._resolve_timezone(request)
        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError):
                timezone.deactivate()
        else:
            timezone.deactivate()

        response = self.get_response(request)
        timezone.deactivate()
        return response

    def _resolve_timezone(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if profile and profile.timezone:
                return profile.timezone
        return request.COOKIES.get('django_timezone')
