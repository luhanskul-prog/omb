from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone


DEFAULT_TIMEZONE = "Africa/Nairobi"


class UserTimezoneMiddleware:
    """
    Activates the logged-in user's preferred timezone for the
    duration of the request.

    The database continues to use UTC because USE_TZ=True.
    Only the displayed/request-local timezone changes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        tz_name = DEFAULT_TIMEZONE

        if getattr(request, "user", None) is not None:
            if request.user.is_authenticated:

                try:
                    profile = request.user.profile
                    tz_name = profile.timezone or DEFAULT_TIMEZONE
                except Exception:
                    tz_name = DEFAULT_TIMEZONE

        try:
            timezone.activate(ZoneInfo(tz_name))
        except (ZoneInfoNotFoundError, ValueError):
            timezone.activate(ZoneInfo(DEFAULT_TIMEZONE))

        response = self.get_response(request)

        timezone.deactivate()

        return response
