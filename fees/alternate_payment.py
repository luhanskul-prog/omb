from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import AlternatePaymentSettings, AlternatePayment, FeePayment
from .payment_method_access import require_automatic_payment
from accounts.staff_access import role_permission_required
from .models import AutomaticPaymentSettings


def _get_branding():
    try:
        from accounts.models import SchoolBranding
        return SchoolBranding.objects.filter(is_active=True).first()
    except Exception:
        return None


def _get_student_model():
    from students.models import Student
    return Student


def _allowed_student(request, student_id=None, admission_no=None):
    """
    Central authorization for Alternate Payment access.

    Staff/Admin:
        Can access any learner.

    Student:
        Can access ONLY request.user.profile.student.

    Parent:
        Can access ONLY request.user.parent.children.

    Admission number:
        Used only to identify the requested learner.
        It NEVER grants authorization by itself.
    """

    Student = _get_student_model()

    # --------------------------------------------------------
    # Resolve requested learner
    # --------------------------------------------------------
    student = None

    if student_id is not None:
        try:
            student = Student.objects.filter(pk=int(student_id)).first()
        except (TypeError, ValueError):
            return None

    elif admission_no:
        admission_no = str(admission_no).strip()

        if not admission_no:
            return None

        student = (
            Student.objects
            .filter(admission_no__iexact=admission_no)
            .first()
        )

    if student is None:
        return None

    # --------------------------------------------------------
    # STAFF / ADMIN
    # --------------------------------------------------------
    if _staff_only(request):
        return student

    # --------------------------------------------------------
    # STUDENT
    # --------------------------------------------------------
    profile = getattr(request.user, "profile", None)

    if profile is not None:
        linked_student_id = getattr(profile, "student_id", None)

        if linked_student_id is not None:
            try:
                if int(linked_student_id) == int(student.pk):
                    return student
            except (TypeError, ValueError):
                pass

    # --------------------------------------------------------
    # PARENT
    # --------------------------------------------------------
    parent = getattr(request.user, "parent", None)

    if parent is not None:
        try:
            if parent.children.filter(pk=student.pk).exists():
                return student
        except Exception:
            pass

    # --------------------------------------------------------
    # NOT AUTHORIZED
    # --------------------------------------------------------
    return None


def _student_balance(student):
    total = Decimal("0.00")

    for record in student.fee_records.all().order_by("id"):
        balance = getattr(record, "balance", 0) or 0
        total += Decimal(str(balance))

    return total


def _payment_settings():
    return AlternatePaymentSettings.objects.filter(pk=1).first()


def _payment_context(payment_settings):
    return {
        "payment_settings": payment_settings,

        "paybill": getattr(
            payment_settings,
            "paybill_number",
            "",
        ),

        "paybill_instructions": getattr(
            payment_settings,
            "paybill_instructions",
            "",
        ),

        "till": getattr(
            payment_settings,
            "till_number",
            "",
        ),

        "till_instructions": getattr(
            payment_settings,
            "till_instructions",
            "",
        ),

        "bank_name": getattr(
            payment_settings,
            "bank_name",
            "",
        ),

        "bank_account_name": getattr(
            payment_settings,
            "bank_account_name",
            "",
        ),

        "bank_account": getattr(
            payment_settings,
            "bank_account_number",
            "",
        ),

        "bank_branch": getattr(
            payment_settings,
            "bank_branch",
            "",
        ),

        "bank_instructions": getattr(
            payment_settings,
            "bank_instructions",
            "",
        ),

        "branding": _get_branding(),
    }




@login_required
def alternate_payment_gateway(request):
    """
    Gateway for Alternate Payment.

    Presents two options:
    1. Automatic Payment
    2. Manual / Wire Payment

    Automatic payment will be implemented separately.
    """

    student_id = request.GET.get("student", "").strip()

    return render(
        request,
        "fees/alternate_payment_gateway.html",
        {
            "branding": _get_branding(),
            "student_id": student_id,
        },
    )


@login_required
def alternate_payment(request):

    admission_no = (
        request.POST.get("admission_no", "")
        if request.method == "POST"
        else request.GET.get("admission_no", "")
    ).strip()

    student_param = (
        request.POST.get("student", "")
        if request.method == "POST"
        else request.GET.get("student", "")
    ).strip()

    student = None

    # If the gateway supplied a student ID, resolve that learner
    # through the existing authorization system.
    if student_param and not admission_no:
        student = _allowed_student(
            request,
            student_id=student_param,
        )

        if student:
            admission_no = student.admission_no
    balance = Decimal("0.00")

    if admission_no:
        student = _allowed_student(request, admission_no=admission_no)

        if student:
            balance = _student_balance(student)

    if request.method == "POST":

        if not student:
            messages.error(
                request,
                "Learner not found or you are not authorized to access this learner.",
            )
            return redirect("fees:alternate_payment")

        method = (
            request.POST.get("payment_method", "")
            .strip()
            .lower()
        )

        if method not in ("paybill", "till", "bank"):
            messages.error(
                request,
                "Please choose a payment method.",
            )
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        # Server-side enforcement of Automatic Payment settings.
        method_map = {
            "paybill": "MPESA_PAYBILL",
            "till": "MPESA_TILL",
            "bank": "BANK",
        }

        try:
            require_automatic_payment(
                method_map[method]
            )
        except RuntimeError as exc:
            messages.error(request, str(exc))
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        amount_text = request.POST.get("amount", "").strip()

        try:
            amount = Decimal(amount_text).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Enter a valid payment amount.",
            )
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        if amount <= 0:
            messages.error(
                request,
                "Payment amount must be greater than zero.",
            )
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        if balance <= 0:
            messages.error(
                request,
                "This learner has no outstanding fee balance.",
            )
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        if amount > balance:
            messages.error(
                request,
                f"Amount cannot exceed the outstanding balance of "
                f"KSh {balance:,.2f}.",
            )
            return redirect(
                f"/fees/alternate/?admission_no={student.admission_no}"
            )

        reference = (
            "ALT-"
            + timezone.now().strftime("%Y%m%d%H%M%S")
            + "-"
            + str(student.admission_no)
        )

        alternate = AlternatePayment.objects.create(
            student=student,
            amount=amount,
            payment_method=method,
            reference=reference,
            status="PENDING",
            external_reference="",
            notes="Awaiting payment confirmation.",
        )

        return redirect(
            "fees:alternate_payment_instructions",
            payment_id=alternate.id,
        )

    context = {
        "student": student,
        "admission_no": admission_no,
        "balance": balance,
    }

    context.update(
        _payment_context(_payment_settings())
    )

    return render(
        request,
        "fees/alternate_payment.html",
        context,
    )


@login_required
def alternate_payment_instructions(request, payment_id):

    payment = get_object_or_404(
        AlternatePayment.objects.select_related("student"),
        id=payment_id,
    )

    student = payment.student

    if _allowed_student(request, admission_no=student.admission_no) is None:
        messages.error(
            request,
            "You are not authorized to view this payment.",
        )
        return redirect("fees:alternate_payment")

    context = {
        "payment": payment,
        "student": student,
    }

    context.update(
        _payment_context(_payment_settings())
    )

    return render(
        request,
        "fees/alternate_payment_instructions.html",
        context,
    )


@login_required
def alternate_payment_status(request, payment_id):

    payment = get_object_or_404(
        AlternatePayment.objects.select_related("student"),
        id=payment_id,
    )

    student = payment.student

    if _allowed_student(request, admission_no=student.admission_no) is None:
        messages.error(
            request,
            "You are not authorized to view this payment.",
        )
        return redirect("fees:alternate_payment")

    context = {
        "payment": payment,
        "student": student,
        "branding": _get_branding(),
    }

    return render(
        request,
        "fees/alternate_payment_status.html",
        context,
    )


def _staff_only(request):

    if request.user.is_superuser:
        return True

    profile = getattr(request.user, "profile", None)
    role = str(getattr(profile, "role", "") or "").upper()

    return role in (
        "ADMIN",
        "SUPERADMIN",
        "DIRECTOR",
        "STAFF",
    )


@login_required
@role_permission_required("view_alternatepayment", "fees")
def alternate_payment_management(request):

    payments = (
        AlternatePayment.objects
        .select_related("student")
        .order_by("-created_at")
    )

    status = (
        request.GET.get("status", "")
        .strip()
        .upper()
    )

    if status in ("PENDING", "CONFIRMED", "REJECTED"):
        payments = payments.filter(status=status)

    return render(
        request,
        "fees/alternate_payment_management.html",
        {
            "payments": payments,
            "status": status,
            "branding": _get_branding(),
        },
    )


@login_required
@role_permission_required("change_alternatepayment", "fees")
def alternate_payment_confirm(request, payment_id):

    if request.method != "POST":
        return redirect("fees:alternate_payment_management")

    external_reference = (
        request.POST.get("external_reference", "")
        .strip()
    )

    if not external_reference:
        messages.error(
            request,
            "Enter the M-Pesa or bank transaction reference.",
        )
        return redirect("fees:alternate_payment_management")

    with transaction.atomic():

        payment = get_object_or_404(
            AlternatePayment.objects
            .select_for_update()
            .select_related("student"),
            id=payment_id,
        )

        if payment.status != "PENDING":
            messages.error(
                request,
                "This alternate payment has already been processed.",
            )
            return redirect("fees:alternate_payment_management")

        remaining = Decimal(str(payment.amount))
        student = payment.student

        records = (
            student.fee_records
            .select_for_update()
            .order_by("id")
        )

        for record in records:

            if remaining <= 0:
                break

            balance = Decimal(
                str(getattr(record, "balance", 0) or 0)
            )

            if balance <= 0:
                continue

            allocation = min(balance, remaining)

            fee_payment = FeePayment.objects.create(
                fee_record=record,
                amount=allocation,
                payment_date=timezone.localdate(),
                receipt_number="",
                payment_method=(
                    "Alternate - "
                    + payment.payment_method.upper()
                ),
                reference=external_reference,
            )

            if not fee_payment.receipt_number:
                fee_payment.receipt_number = (
                    f"ALT{fee_payment.id:06d}RCP"
                )
                fee_payment.save(
                    update_fields=["receipt_number"]
                )

            remaining -= allocation

        if remaining > 0:
            messages.error(
                request,
                "The learner's current fee balance is lower than "
                "the alternate payment amount.",
            )
            return redirect(
                "fees:alternate_payment_management"
            )

        payment.external_reference = external_reference
        payment.status = "CONFIRMED"
        payment.verified_at = timezone.now()
        payment.notes = (
            "Confirmed by "
            + request.user.get_username()
            + "."
        )

        payment.save(
            update_fields=[
                "external_reference",
                "status",
                "verified_at",
                "notes",
            ]
        )

    messages.success(
        request,
        "Alternate payment confirmed successfully.",
    )

    return redirect(
        "fees:alternate_payment_management"
    )


@login_required
@role_permission_required("change_alternatepayment", "fees")
def alternate_payment_reject(request, payment_id):

    if request.method != "POST":
        return redirect("fees:alternate_payment_management")

    payment = get_object_or_404(
        AlternatePayment,
        id=payment_id,
    )

    if payment.status != "PENDING":
        messages.error(
            request,
            "Only pending payments can be rejected.",
        )
        return redirect(
            "fees:alternate_payment_management"
        )

    notes = (
        request.POST.get("notes", "")
        .strip()
    )

    payment.status = "REJECTED"
    payment.verified_at = timezone.now()
    payment.notes = (
        notes
        or "Rejected by "
        + request.user.get_username()
        + "."
    )

    payment.save(
        update_fields=[
            "status",
            "verified_at",
            "notes",
        ]
    )

    messages.success(
        request,
        "Alternate payment rejected.",
    )

    return redirect(
        "fees:alternate_payment_management"
    )
@login_required
def alternate_payment_track_request(request):
    reference = request.GET.get("reference", "").strip()

    payment = None
    error = ""

    if reference:
        payment = (
            AlternatePayment.objects
            .select_related("student")
            .filter(reference__iexact=reference)
            .first()
        )

        if not payment:
            error = "No alternate payment request was found with that Request Reference."

        else:
            # NEVER allow a user to load another learner's request
            # merely by knowing the reference.
            authorized_student = _allowed_student(
                request,
                student_id=payment.student_id,
            )

            if authorized_student is None:
                payment = None
                error = "You are not authorized to view this payment request."

    return render(
        request,
        "fees/alternate_payment_track.html",
        {
            "payment": payment,
            "reference": reference,
            "error": error,
            "branding": _get_branding(),
        },
    )
