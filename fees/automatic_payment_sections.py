
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from accounts.staff_access import role_permission_required

from .models import AutomaticPaymentSettings
from .automatic_payment_section_forms import (
    MpesaOnlineSettingsForm,
    MpesaTillSettingsForm,
    MpesaPaybillSettingsForm,
    BankSettingsForm,
)


def _automatic_payment_admin_allowed(request):
    if request.user.is_superuser:
        return True

    return request.user.profile.custom_role.permissions.filter(
        codename="change_automaticpaymentsettings",
        content_type__app_label="fees",
    ).exists()


def _automatic_payment_settings():
    settings, created = AutomaticPaymentSettings.objects.get_or_create(pk=1)
    return settings


def _save_settings_form(request, form, success_message, redirect_name):

    if form.is_valid():

        form.save()

        messages.success(
            request,
            success_message
        )

        return redirect(redirect_name)

    return None


# ============================================================
# MASTER / SELECT PAYMENT METHOD
# ============================================================

@login_required
def automatic_payment_settings_home(request):

    if not _automatic_payment_admin_allowed(request):
        return redirect("accounts:dashboard")

    settings = _automatic_payment_settings()

    if request.method == "POST":

        environment = request.POST.get("environment")

        if environment in ["sandbox", "production"]:
            settings.environment = environment

        settings.is_active = (
            request.POST.get("is_active") == "on"
        )

        settings.save()

        messages.success(
            request,
            "General automatic payment settings saved successfully."
        )

        return redirect(
            "fees:automatic_payment_settings"
        )

    return render(
        request,
        "fees/automatic_payment_settings_home.html",
        {
            "settings": settings,
            "automatic_payment_settings": settings,
        }
    )


# ============================================================
# M-PESA ONLINE
# ============================================================

@login_required
def mpesa_online_settings(request):

    if not _automatic_payment_admin_allowed(request):
        return redirect("accounts:dashboard")

    settings = _automatic_payment_settings()

    if request.method == "POST":

        form = MpesaOnlineSettingsForm(
            request.POST,
            instance=settings
        )

        result = _save_settings_form(
            request,
            form,
            "M-Pesa Online settings saved successfully.",
            "fees:mpesa_online_settings"
        )

        if result:
            return result

    else:

        form = MpesaOnlineSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/mpesa_online_settings.html",
        {
            "form": form,
            "settings": settings,
            "automatic_payment_settings": settings,
        }
    )


# ============================================================
# M-PESA TILL
# ============================================================

@login_required
def mpesa_till_settings(request):

    if not _automatic_payment_admin_allowed(request):
        return redirect("accounts:dashboard")

    settings = _automatic_payment_settings()

    if request.method == "POST":

        form = MpesaTillSettingsForm(
            request.POST,
            instance=settings
        )

        result = _save_settings_form(
            request,
            form,
            "M-Pesa Till settings saved successfully.",
            "fees:mpesa_till_settings"
        )

        if result:
            return result

    else:

        form = MpesaTillSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/mpesa_till_settings.html",
        {
            "form": form,
            "settings": settings,
            "automatic_payment_settings": settings,
        }
    )


# ============================================================
# M-PESA PAYBILL
# ============================================================

@login_required
def mpesa_paybill_settings(request):

    if not _automatic_payment_admin_allowed(request):
        return redirect("accounts:dashboard")

    settings = _automatic_payment_settings()

    # Keep existing callback URLs if already configured.
    # Otherwise show the actual ERP callback endpoints.
    validation_path = reverse(
        "fees:paybill_c2b_validation"
    )

    confirmation_path = reverse(
        "fees:paybill_c2b_confirmation"
    )

    validation_url = (
        settings.mpesa_paybill_validation_url
        or request.build_absolute_uri(validation_path)
    )

    confirmation_url = (
        settings.mpesa_paybill_confirmation_url
        or request.build_absolute_uri(confirmation_path)
    )

    if request.method == "POST":

        form = MpesaPaybillSettingsForm(
            request.POST,
            instance=settings
        )

        result = _save_settings_form(
            request,
            form,
            "M-Pesa PayBill settings saved successfully.",
            "fees:mpesa_paybill_settings"
        )

        if result:
            return result

    else:

        form = MpesaPaybillSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/mpesa_paybill_settings.html",
        {
            "form": form,
            "settings": settings,
            "automatic_payment_settings": settings,
            "paybill_validation_url": validation_url,
            "paybill_confirmation_url": confirmation_url,
        }
    )


# ============================================================
# BANK
# ============================================================

@login_required
def bank_settings(request):

    if not _automatic_payment_admin_allowed(request):
        return redirect("accounts:dashboard")

    settings = _automatic_payment_settings()

    # ========================================================
    # BANK CONNECTION TEST
    # ========================================================
    if request.method == "POST" and request.POST.get("action") == "test_bank":

        from django.contrib import messages
        from django.utils import timezone

        required = []

        if not settings.bank_name:
            required.append("Bank name")

        if not settings.bank_account_number:
            required.append("Bank account number")

        if not settings.bank_transaction_endpoint:
            required.append("Transaction Endpoint")

        auth_method = (
            getattr(settings, "bank_authentication_method", "") or ""
        ).strip().upper()

        if auth_method == "OAUTH 2.0":
            if not settings.bank_client_id:
                required.append("Client ID")
            if not settings.bank_client_secret:
                required.append("Client Secret")
            if not settings.bank_access_token_url:
                required.append("Access Token URL")

        elif auth_method == "API KEY":
            if not settings.bank_api_key:
                required.append("API Key")

        elif auth_method == "BASIC AUTHENTICATION":
            if not settings.bank_client_id:
                required.append("Username / Client ID")
            if not settings.bank_client_secret:
                required.append("Password / Client Secret")

        elif auth_method == "BEARER TOKEN":
            if not settings.bank_api_key and not settings.bank_client_secret:
                required.append("Bearer Token")

        if not settings.is_active:
            required.append("Automatic Payments must be enabled")

        if not settings.bank_enabled:
            required.append("Bank automatic verification must be enabled")

        if required:

            settings.bank_verification_status = (
                "NOT CONFIGURED: " + ", ".join(required)[:180]
            )

            settings.save(
                update_fields=["bank_verification_status"]
            )

            messages.error(
                request,
                "Bank integration is incomplete: "
                + ", ".join(required)
            )

            return redirect("fees:bank_settings")

        try:

            from .bank_integration_engine import (
                fetch_transactions_from_configured_bank
            )

            integration_result = (
                fetch_transactions_from_configured_bank(settings)
            )

            payload = integration_result.get("payload", {})

            if isinstance(payload, list):

                transaction_count = len(payload)

            elif isinstance(payload, dict):

                possible = (
                    payload.get("transactions")
                    or payload.get("Transactions")
                    or payload.get("data")
                    or payload.get("Data")
                    or []
                )

                transaction_count = (
                    len(possible)
                    if isinstance(possible, list)
                    else 0
                )

            else:

                transaction_count = 0

            bank_label = integration_result.get(
                "bank",
                settings.bank_name or "Bank"
            )

            settings.bank_verification_status = (
                "CONNECTION OK - "
                + str(bank_label)
                + " transaction service reachable"
            )

            settings.bank_last_sync = timezone.now()

            settings.save(
                update_fields=[
                    "bank_verification_status",
                    "bank_last_sync",
                ]
            )

            messages.success(
                request,
                f"Bank connection successful. "
                f"{bank_label} transaction service responded. "
                f"{transaction_count} transaction(s) returned."
            )

        except Exception as exc:

            error_text = (
                str(exc)
                .replace("\n", " ")
                .strip()
            )

            settings.bank_verification_status = (
                "CONNECTION FAILED: "
                + error_text[:180]
            )

            settings.save(
                update_fields=["bank_verification_status"]
            )

            messages.error(
                request,
                "Bank connection test failed: "
                + error_text[:500]
            )

        return redirect("fees:bank_settings")

    # ========================================================
    # NORMAL BANK SETTINGS SAVE
    # ========================================================

    if request.method == "POST":

        form = BankSettingsForm(
            request.POST,
            instance=settings
        )

        result = _save_settings_form(
            request,
            form,
            "Bank automatic payment settings saved successfully.",
            "fees:bank_settings"
        )

        if result:
            return result

    else:

        form = BankSettingsForm(
            instance=settings
        )

    return render(
        request,
        "fees/bank_settings.html",
        {
            "form": form,
            "settings": settings,
            "automatic_payment_settings": settings,
        }
    )

