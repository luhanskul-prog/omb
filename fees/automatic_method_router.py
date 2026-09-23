from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .alternate_payment_auto import (
    _automatic_payment_settings,
    _branding,
    _load_student_data,
)
from .payment_method_access import require_automatic_payment


@login_required
def automatic_online_route(request):
    """
    M-Pesa Online entry point.

    Uses the M-Pesa Online configuration from AutomaticPaymentSettings.
    The actual proven Online STK flow remains unchanged.
    """
    admission_no = (
        request.GET.get("admission_no", "")
        or request.POST.get("admission_no", "")
    ).strip()

    try:
        require_automatic_payment("MPESA_ONLINE")
        student, fee_record, balance = _load_student_data(
            request,
            admission_no,
        )
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("fees:alternate_payment_auto_method")

    return redirect(
        f"{reverse('fees:online_payment')}"
        f"?student_id={student.id}&fee_record_id={fee_record.id}"
    )


@login_required
def automatic_till_route(request):
    """
    M-Pesa Till entry point.

    Uses the Till configuration from AutomaticPaymentSettings.
    """
    admission_no = (
        request.GET.get("admission_no", "")
        or request.POST.get("admission_no", "")
    ).strip()

    try:
        require_automatic_payment("MPESA_TILL")
        _load_student_data(request, admission_no)
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("fees:alternate_payment_auto_method")

    return redirect(
        f"{reverse('fees:alternate_till_payment')}"
        f"?admission_no={admission_no}"
    )


@login_required
def automatic_paybill_route(request):
    """
    M-Pesa PayBill payment page.

    Reads:
        mpesa_paybill_number
        mpesa_paybill_account
        mpesa_paybill_shortcode
        mpesa_paybill_consumer_key
        mpesa_paybill_consumer_secret
        mpesa_paybill_passkey
        mpesa_paybill_validation_url
        mpesa_paybill_confirmation_url

    from AutomaticPaymentSettings.
    """
    admission_no = (
        request.GET.get("admission_no", "")
        or request.POST.get("admission_no", "")
    ).strip()

    try:
        require_automatic_payment("MPESA_PAYBILL")
        student, fee_record, balance = _load_student_data(
            request,
            admission_no,
        )
    except Exception as exc:
        return render(
            request,
            "fees/paybill_payment.html",
            {
                "branding": _branding(),
                "automatic_payment_settings": _automatic_payment_settings(),
                "admission_no": admission_no,
                "error": str(exc),
            },
            status=403,
        )

    settings = _automatic_payment_settings()

    if balance <= Decimal("0.00"):
        return render(
            request,
            "fees/paybill_payment.html",
            {
                "branding": _branding(),
                "automatic_payment_settings": settings,
                "student": student,
                "fee_record": fee_record,
                "balance": balance,
                "admission_no": admission_no,
                "error": "This learner has no outstanding fee balance.",
            },
        )

    return render(
        request,
        "fees/paybill_payment.html",
        {
            "branding": _branding(),
            "automatic_payment_settings": settings,
            "student": student,
            "fee_record": fee_record,
            "balance": balance,
            "admission_no": admission_no,
        },
    )


@login_required
def automatic_bank_route(request):
    """
    Bank payment entry point.

    Uses only the Bank configuration from AutomaticPaymentSettings.
    """
    admission_no = (
        request.GET.get("admission_no", "")
        or request.POST.get("admission_no", "")
    ).strip()

    try:
        require_automatic_payment("BANK")
        _load_student_data(request, admission_no)
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("fees:alternate_payment_auto_method")

    return redirect(
        f"{reverse('fees:bank_payment')}"
        f"?admission_no={admission_no}"
    )
