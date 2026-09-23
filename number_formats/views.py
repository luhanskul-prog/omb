
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import SchoolNumberSettings
from .forms import SchoolNumberSettingsForm


def _is_admin(request):
    if request.user.is_superuser:
        return True

    profile = getattr(request.user, "profile", None)
    role = str(getattr(profile, "role", "") or "").upper()

    return role in ("ADMIN", "SUPERADMIN", "DIRECTOR")


@login_required
def number_format_settings(request):

    if not _is_admin(request):
        return redirect("accounts:dashboard")

    settings, created = SchoolNumberSettings.objects.get_or_create(pk=1)

    if request.method == "POST":
        form = SchoolNumberSettingsForm(
            request.POST,
            instance=settings
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Student and employee number formats saved successfully."
            )
            return redirect("number_formats:settings")
    else:
        form = SchoolNumberSettingsForm(instance=settings)

    return render(
        request,
        "number_formats/settings.html",
        {
            "form": form,
            "settings": settings,
            "student_example": settings.student_example(),
            "employee_example": settings.employee_example(),
        }
    )
