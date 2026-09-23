
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render, redirect
from accounts.staff_access import role_permission_required

from .models import AlternatePaymentSettings
from .alternate_payment_settings import AlternatePaymentSettingsForm
from .models import AutomaticPaymentSettings
from .automatic_payment_settings import AutomaticPaymentSettingsForm


@login_required
@role_permission_required("change_alternatepaymentsettings", "fees")
def alternate_payment_settings(request):


    settings, created = AlternatePaymentSettings.objects.get_or_create(
        pk=1
    )

    if request.method == "POST":

        form = AlternatePaymentSettingsForm(
            request.POST,
            instance=settings
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Alternate payment settings saved successfully."
            )

            return redirect(
                "fees:alternate_payment_settings"
            )

    else:

        form = AlternatePaymentSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/alternate_payment_settings.html",
        {
            "form": form,
            "settings": settings,
        }
    )


@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def automatic_payment_settings(request):


    settings, created = AutomaticPaymentSettings.objects.get_or_create(
        pk=1
    )

    if request.method == "POST":
        form = AutomaticPaymentSettingsForm(
            request.POST,
            instance=settings
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Automatic payment settings saved successfully."
            )

            return redirect(
                "fees:automatic_payment_settings"
            )

    else:
        form = AutomaticPaymentSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/automatic_payment_settings.html",
        {
            "form": form,
            "settings": settings,
        }
    )
