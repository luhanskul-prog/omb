
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.staff_access import role_permission_required

from .models import (
    AutomaticPaymentSettings,
    MpesaPaybillTransaction,
)
from .mpesa_paybill_c2b import (
    register_c2b_urls,
    save_confirmation,
    validate_c2b_payload,
)


def _json_body(request):
    try:
        body = request.body.decode("utf-8")
        return json.loads(body or "{}")
    except Exception:
        return {}


@csrf_exempt
@require_http_methods(["POST"])
def c2b_validation(request):
    payload = _json_body(request)

    ok, message = validate_c2b_payload(payload)

    if ok:
        return JsonResponse({
            "ResultCode": 0,
            "ResultDesc": "Accepted",
        })

    return JsonResponse({
        "ResultCode": 1,
        "ResultDesc": message,
    })


@csrf_exempt
@require_http_methods(["POST"])
def c2b_confirmation(request):
    payload = _json_body(request)

    try:
        c2b, created = save_confirmation(payload)

        if c2b.status == "VERIFIED":
            description = "Payment received and automatically verified."
        elif c2b.status == "DUPLICATE":
            description = "Payment already processed."
        elif c2b.status == "REJECTED":
            description = c2b.verification_message or "Payment rejected."
        else:
            description = c2b.verification_message or "Payment received."

        return JsonResponse({
            "ResultCode": 0,
            "ResultDesc": description,
        })

    except Exception as exc:
        return JsonResponse({
            "ResultCode": 1,
            "ResultDesc": f"Payment processing error: {exc}",
        })


@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def c2b_register_urls(request):

    config = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not config:
        messages.error(
            request,
            "Automatic payment settings are not configured.",
        )
        return redirect("fees:automatic_payment_settings")

    if not config.is_active:
        messages.error(
            request,
            "Automatic payments are currently disabled.",
        )
        return redirect("fees:automatic_payment_settings")

    if not config.mpesa_paybill_enabled:
        messages.error(
            request,
            "M-Pesa PayBill automation is disabled.",
        )
        return redirect("fees:automatic_payment_settings")

    try:
        result = register_c2b_urls()

        config.mpesa_paybill_validation_url = (
            request.build_absolute_uri(
                "/fees/paybill/c2b/validation/"
            )
        )

        config.mpesa_paybill_confirmation_url = (
            request.build_absolute_uri(
                "/fees/paybill/c2b/confirmation/"
            )
        )

        config.save(
            update_fields=[
                "mpesa_paybill_validation_url",
                "mpesa_paybill_confirmation_url",
            ]
        )

        messages.success(
            request,
            "M-Pesa PayBill C2B URLs registered successfully.",
        )

        messages.info(
            request,
            f"Safaricom response: {result}",
        )

    except Exception as exc:
        messages.error(
            request,
            f"C2B URL registration failed: {exc}",
        )

    return redirect("fees:automatic_payment_settings")


@login_required
@role_permission_required("view_mpesapaybilltransaction", "fees")
def c2b_transactions(request):

    transactions = (
        MpesaPaybillTransaction.objects
        .select_related(
            "student",
            "fee_record",
            "fee_payment",
        )
        .order_by("-created_at")[:200]
    )

    return render(
        request,
        "fees/paybill_c2b_transactions.html",
        {
            "transactions": transactions,
        },
    )
