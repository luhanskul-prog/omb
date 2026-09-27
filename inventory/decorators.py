from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect


def inventory_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        profile = getattr(request.user, "userprofile", None)
        role = getattr(profile, "role", "") if profile else ""
        allowed = request.user.is_superuser or request.user.is_staff or role in {"ADMIN", "STAFF"}
        if not allowed:
            messages.error(request, "You do not have permission to access Inventory.")
            return redirect("/")
        return view_func(request, *args, **kwargs)
    return wrapper
