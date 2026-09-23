
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from .services.automatic_mpesa import initiate_automatic_stk_push
from django.views.decorators.http import require_http_methods

from students.models import Student
from .models import FeeRecord, OnlinePayment, AutomaticPaymentSettings
from .services.mpesa import MpesaError, initiate_stk_push
from .services.online_payments import (
    OnlinePaymentError,
    create_online_payment,
)
from .payment_method_access import require_automatic_payment


def _branding():
    try:
        from accounts.models import SchoolBranding
        return SchoolBranding.objects.filter(is_active=True).first()
    except Exception:
        return None


def _automatic_payment_settings():
    """
    Return the single live automatic-payment configuration.

    Parent and Student portals use this same database record,
    so administrator changes are reflected automatically.
    """
    return AutomaticPaymentSettings.objects.filter(pk=1).first()


def _payer_role(request):
    profile = getattr(request.user, "profile", None)

    if not profile:
        return None

    role = str(getattr(profile, "role", "") or "").upper()

    if role in {"ADMIN", "PARENT", "STUDENT"}:
        return role

    return None


def _staff_access(request):
    profile = getattr(request.user, "profile", None)

    if request.user.is_superuser:
        return True

    role = str(getattr(profile, "role", "") or "").upper()

    return role in {
        "ADMIN",
        "SUPERADMIN",
        "DIRECTOR",
        "STAFF",
    }


def _authorized_student(request, admission_no):
    admission_no = str(admission_no or "").strip()

    if not admission_no:
        return None

    student = (
        Student.objects
        .filter(
            admission_no__iexact=admission_no,
            is_active=True,
        )
        .first()
    )

    if not student:
        return None

    # Staff/Admin can access learners.
    if _staff_access(request):
        return student

    profile = getattr(request.user, "profile", None)

    # Student can pay only their own fees.
    if profile is not None:
        linked_student_id = getattr(
            profile,
            "student_id",
            None,
        )

        if linked_student_id == student.id:
            return student

    # Parent can pay only for linked children.
    parent = getattr(request.user, "parent", None)

    if parent is not None:
        try:
            if parent.children.filter(
                pk=student.pk
            ).exists():
                return student
        except Exception:
            pass

    return None


def _current_fee_record(student):
    """
    Select the learner's currently payable fee record.

    Priority:
    1. Active academic year + active term
    2. Latest record belonging to an active term
    3. Latest record overall as a safe fallback
    """

    records = (
        FeeRecord.objects
        .filter(student=student)
        .select_related(
            "student",
            "academic_year",
            "term",
        )
    )

    # Current active year + active term.
    current = (
        records
        .filter(
            academic_year__is_active=True,
            term__is_active=True,
            term__is_closed=False,
        )
        .order_by(
            "-academic_year__year",
            "-term__order",
            "-id",
        )
        .first()
    )

    if current:
        return current

    # Fallback: newest open active term.
    current = (
        records
        .filter(
            term__is_active=True,
            term__is_closed=False,
        )
        .order_by(
            "-academic_year__year",
            "-term__order",
            "-id",
        )
        .first()
    )

    if current:
        return current

    # Final fallback prevents the screen from becoming unusable
    # if term configuration is temporarily incomplete.
    return records.order_by(
        "-academic_year__year",
        "-term__order",
        "-id",
    ).first()


def _load_student_data(request, admission_no):
    student = _authorized_student(
        request,
        admission_no,
    )

    if student is None:
        raise OnlinePaymentError(
            "Learner not found, inactive, or you are not authorized "
            "to make payment for this learner."
        )

    fee_record = _current_fee_record(student)

    if fee_record is None:
        raise OnlinePaymentError(
            "No fee record is available for this learner."
        )

    balance = Decimal(
        str(fee_record.balance or 0)
    ).quantize(Decimal("0.01"))

    return student, fee_record, balance


@require_http_methods(["GET", "POST"])
@login_required
def alternate_payment_auto(request):

    payer_role = _payer_role(request)

    if payer_role not in {
        "ADMIN",
        "PARENT",
        "STUDENT",
    }:
        messages.error(
            request,
            "Your account is not authorized to make online payment.",
        )
        return redirect("accounts:login")

    admission_no = (
        request.POST.get("admission_no")
        or request.GET.get("admission_no")
        or ""
    ).strip()

    selected_method = (
        request.POST.get("method")
        or request.GET.get("method")
        or "online"
    ).strip().lower()

    student = None
    fee_record = None
    balance = None
    error = ""

    # --------------------------------------------------------
    # LOAD BALANCE
    # --------------------------------------------------------

    action = request.POST.get("action", "").strip()

    if action == "select_mpesa":
        try:
            student, fee_record, balance = _load_student_data(
                request,
                admission_no,
            )

            if balance <= Decimal("0.00"):
                error = (
                    "This learner has no outstanding fee balance."
                )

        except OnlinePaymentError as exc:
            error = str(exc)

    elif action == "lookup" and admission_no:
        try:
            student, fee_record, balance = _load_student_data(
                request,
                admission_no,
            )

            if balance <= Decimal("0.00"):
                error = (
                    "This learner has no outstanding fee balance."
                )

        except OnlinePaymentError as exc:
            error = str(exc)

    # --------------------------------------------------------
    # PAY NOW
    # --------------------------------------------------------

    elif action == "pay":
        try:
            # Enforce the administrator's automatic M-Pesa Online
            # enable/disable setting on the server.
            require_automatic_payment("MPESA_ONLINE")

            student, fee_record, balance = _load_student_data(
                request,
                admission_no,
            )

            if balance <= Decimal("0.00"):
                raise OnlinePaymentError(
                    "This learner has no outstanding fee balance."
                )

            phone_number = (
                request.POST.get("phone_number", "")
                .strip()
            )

            raw_amount = (
                request.POST.get("amount", "")
                .strip()
            )

            try:
                amount = Decimal(raw_amount)
            except (InvalidOperation, TypeError, ValueError):
                raise OnlinePaymentError(
                    "Enter a valid payment amount."
                )

            amount = amount.quantize(
                Decimal("0.01")
            )

            if amount <= Decimal("0.00"):
                raise OnlinePaymentError(
                    "Payment amount must be greater than zero."
                )

            if amount > balance:
                raise OnlinePaymentError(
                    f"Payment cannot exceed the outstanding "
                    f"balance of KSh {balance:,.2f}."
                )

            # Create OnlinePayment using the existing service.
            online_payment = create_online_payment(
                payer=request.user,
                payer_role=payer_role,
                student=student,
                fee_record_id=fee_record.id,
                amount=amount,
                payment_method_code="MPESA",
                phone_number=phone_number,
            )

            # Existing Daraja STK service.
            try:
                response = initiate_automatic_stk_push(
                    phone_number=online_payment.phone_number,
                    amount=online_payment.amount,
                    method="MPESA_ONLINE",
                    account_reference=(
                        online_payment.account_reference
                        or f"FEES-{online_payment.id}"
                    ),
                )
            except (MpesaError, RuntimeError) as exc:
                online_payment.status = "FAILED"
                online_payment.verification_message = (
                    f"Unable to send the M-Pesa payment prompt: {exc}"
                )
                online_payment.save(
                    update_fields=[
                        "status",
                        "verification_message",
                        "updated_at",
                    ]
                )
                raise

            online_payment.merchant_request_id = (
                response.get("MerchantRequestID", "")
                or ""
            )
            online_payment.checkout_request_id = (
                response.get("CheckoutRequestID", "")
                or ""
            )
            online_payment.provider_response_code = (
                str(
                    response.get("ResponseCode", "")
                    or ""
                )
            )
            online_payment.provider_response_description = (
                response.get("ResponseDescription", "")
                or ""
            )
            online_payment.provider_raw_response = response

            if str(
                response.get("ResponseCode", "")
                or ""
            ) == "0":
                online_payment.status = "PROCESSING"
                online_payment.verification_message = (
                    "M-Pesa payment prompt sent to your phone. "
                    "Complete the payment on your phone."
                )
            else:
                online_payment.status = "FAILED"
                online_payment.verification_message = (
                    response.get("ResponseDescription", "")
                    or "M-Pesa payment request failed."
                )

            online_payment.save()

            return redirect(
                "fees:online_payment_status",
                payment_id=online_payment.id,
            )

        except (OnlinePaymentError, MpesaError) as exc:
            error = str(exc)

    return render(
        request,
        "fees/alternate_payment_auto.html",
        {
            "branding": _branding(),
            "student": student,
            "fee_record": fee_record,
            "balance": balance,
            "admission_no": admission_no,
            "error": error,
            "payer_role": payer_role,
            "selected_method": selected_method,
            "automatic_payment_settings": _automatic_payment_settings(),
        },
    )


@login_required
@require_http_methods(["GET"])
def alternate_payment_auto_method(request):
    """
    Payment-method selection page.

    The learner is re-authorized here instead of trusting the
    admission number in the URL.
    """
    admission_no = (
        request.GET.get("admission_no", "")
        or ""
    ).strip()

    try:
        student, fee_record, balance = _load_student_data(
            request,
            admission_no,
        )
    except OnlinePaymentError as exc:
        messages.error(request, str(exc))
        return redirect(
            "fees:alternate_payment_auto"
        )

    if balance <= Decimal("0.00"):
        messages.error(
            request,
            "This learner has no outstanding fee balance.",
        )
        return redirect(
            "fees:alternate_payment_auto"
        )

    # IMPORTANT:
    # Parent and Student automatic-payment screens must use
    # AutomaticPaymentSettings, not the old manual settings.
    payment_settings = _automatic_payment_settings()

    return render(
        request,
        "fees/alternate_payment_auto_method.html",
        {
            "branding": _branding(),
            "student": student,
            "fee_record": fee_record,
            "balance": balance,
            "admission_no": admission_no,
            "payment_settings": payment_settings,
            "automatic_payment_settings": payment_settings,
            "selected_method": (
                request.GET.get("method", "")
                or "online"
            ).strip().lower(),
        },
    )
