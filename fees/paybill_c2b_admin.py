
import requests

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from accounts.staff_access import role_permission_required

from .models import AutomaticPaymentSettings
from .mpesa_paybill_c2b import (
    get_access_token,
    register_c2b_urls,
)


def _callback_urls(request):
    validation_url = request.build_absolute_uri(
        reverse("fees:paybill_c2b_validation")
    )

    confirmation_url = request.build_absolute_uri(
        reverse("fees:paybill_c2b_confirmation")
    )

    return validation_url, confirmation_url


@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def test_paybill_credentials(request):
    if request.method != "POST":
        return redirect("fees:automatic_payment_settings")

    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        messages.error(request, "Automatic payment settings have not been created.")
        return redirect("fees:automatic_payment_settings")

    # Testing is allowed before PayBill is activated.
    # This lets the administrator configure and verify credentials first.

    missing = []

    if not settings.mpesa_paybill_number:
        missing.append("PayBill Number")

    if not settings.mpesa_paybill_shortcode:
        missing.append("Short Code")

    if not settings.mpesa_paybill_consumer_key:
        missing.append("Consumer Key")

    if not settings.mpesa_paybill_consumer_secret:
        missing.append("Consumer Secret")

    if missing:
        messages.error(
            request,
            "PayBill configuration incomplete. Missing: "
            + ", ".join(missing)
        )
        return redirect("fees:automatic_payment_settings")

    try:
        token = get_access_token()

        if not token:
            raise RuntimeError("Safaricom did not return an access token.")

        settings.mpesa_paybill_confirmation_url = (
            _callback_urls(request)[1]
        )
        settings.mpesa_paybill_validation_url = (
            _callback_urls(request)[0]
        )
        settings.save(
            update_fields=[
                "mpesa_paybill_confirmation_url",
                "mpesa_paybill_validation_url",
            ]
        )

        messages.success(
            request,
            "PayBill credentials TEST PASSED. Safaricom access token obtained successfully."
        )

    except Exception as exc:
        messages.error(
            request,
            f"PayBill credential test FAILED: {exc}"
        )

    return redirect("fees:automatic_payment_settings")


@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def register_paybill_c2b(request):
    if request.method != "POST":
        return redirect("fees:automatic_payment_settings")

    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        messages.error(request, "Automatic payment settings have not been created.")
        return redirect("fees:automatic_payment_settings")

    # C2B registration is allowed before activation.
    # Activation happens only after successful configuration.
    validation_url, confirmation_url = _callback_urls(request)

    try:
        # First verify that credentials work.
        token = get_access_token()

        if not token:
            raise RuntimeError("Unable to obtain Safaricom access token.")

        # Register the ERP callback URLs with Safaricom.
        result = register_c2b_urls(
            confirmation_url=confirmation_url,
            validation_url=validation_url,
        )

        settings.mpesa_paybill_validation_url = validation_url
        settings.mpesa_paybill_confirmation_url = confirmation_url
        settings.save(
            update_fields=[
                "mpesa_paybill_validation_url",
                "mpesa_paybill_confirmation_url",
            ]
        )

        messages.success(
            request,
            "PayBill C2B registration completed successfully. "
            "Safaricom callback URLs are now registered."
        )

    except Exception as exc:
        messages.error(
            request,
            f"PayBill C2B registration FAILED: {exc}"
        )

    return redirect("fees:automatic_payment_settings")


@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def activate_paybill(request):
    if request.method != "POST":
        return redirect("fees:automatic_payment_settings")

    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        messages.error(request, "Automatic payment settings have not been created.")
        return redirect("fees:automatic_payment_settings")

    required = {
        "PayBill Number": settings.mpesa_paybill_number,
        "Short Code": settings.mpesa_paybill_shortcode,
        "Consumer Key": settings.mpesa_paybill_consumer_key,
        "Consumer Secret": settings.mpesa_paybill_consumer_secret,
        "Validation URL": settings.mpesa_paybill_validation_url,
        "Confirmation URL": settings.mpesa_paybill_confirmation_url,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        messages.error(
            request,
            "Cannot activate PayBill automation. Missing: "
            + ", ".join(missing)
        )
        return redirect("fees:automatic_payment_settings")

    try:
        token = get_access_token()

        if not token:
            raise RuntimeError("Safaricom credential test failed.")

        # Activate the master automatic-payment switch and PayBill.
        settings.is_active = True
        settings.mpesa_paybill_enabled = True

        settings.save(
            update_fields=[
                "is_active",
                "mpesa_paybill_enabled",
            ]
        )

        messages.success(
            request,
            "M-Pesa PayBill automatic verification is now ACTIVE."
        )

    except Exception as exc:
        messages.error(
            request,
            f"PayBill activation failed: {exc}"
        )

    return redirect("fees:automatic_payment_settings")
