import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from students.models import Student
from .models import FeeRecord, FeePayment, TillPaymentIntent

logger = logging.getLogger(__name__)


def _money(value):
    try:
        return Decimal(str(value or "0")).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def _normalise(value):
    return (
        str(value or "")
        .strip()
        .upper()
        .replace(" ", "")
        .replace("-", "")
    )


def _normalise_phone(value):
    value = re_phone = str(value or "").strip()

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    if digits.startswith("254"):
        return digits

    if digits.startswith("0"):
        return "254" + digits[1:]

    if digits.startswith("7") or digits.startswith("1"):
        return "254" + digits

    return digits


def _student_from_reference(reference):
    ref = _normalise(reference)

    if not ref:
        return None

    return (
        Student.objects
        .filter(admission_no__iexact=ref)
        .first()
    )


def _student_balance(student):
    total = Decimal("0.00")

    records = (
        FeeRecord.objects
        .filter(student=student)
        .order_by("id")
    )

    for record in records:
        total += _money(record.balance)

    return total


def _allocate_payment(student, amount, receipt_number):
    remaining = _money(amount)

    if remaining <= 0:
        return []

    created = []

    records = (
        FeeRecord.objects
        .filter(student=student)
        .order_by("id")
    )

    for record in records:
        balance = _money(record.balance)

        if balance <= 0:
            continue

        if remaining <= 0:
            break

        applied = min(balance, remaining)

        payment = FeePayment.objects.create(
            fee_record=record,
            amount=applied,
            payment_date=timezone.localdate(),
            receipt_number="",
            payment_method="M-Pesa Till",
            reference=receipt_number,
        )

        created.append(payment)
        remaining -= applied

    return created


def _automatic_settings():
    return AutomaticPaymentSettings.objects.filter(pk=1).first()


def _configured_till_number():
    config = _automatic_settings()

    if config:
        value = str(
            config.mpesa_till_number or ""
        ).strip()

        if value:
            return value

    return str(
        getattr(
            settings,
            "ALTERNATE_MPESA_TILL",
            "",
        ) or ""
    ).strip()


def _configured_till_shortcode():
    config = _automatic_settings()

    if config:
        value = str(
            config.mpesa_till_shortcode or ""
        ).strip()

        if value:
            return value

    return _configured_till_number()


def _is_configured_shortcode(shortcode):
    shortcode = str(shortcode or "").strip()

    if not shortcode:
        return True

    allowed = {
        str(getattr(settings, "ALTERNATE_MPESA_PAYBILL", "") or "").strip(),
        str(getattr(settings, "ALTERNATE_MPESA_TILL", "") or "").strip(),
    }

    allowed.discard("")

    if not allowed:
        return True

    return shortcode in allowed


@csrf_exempt
@require_POST
def alternate_c2b_validation(request):
    """
    C2B validation endpoint.

    Supports both the configured PayBill and Till.
    For Till payments, learner matching is performed at
    confirmation using the pending payment intent.
    """

    try:
        payload = json.loads(
            request.body.decode("utf-8") or "{}"
        )
    except Exception:
        return JsonResponse({
            "ResultCode": "C2B00011",
            "ResultDesc": "Invalid JSON",
        })

    reference = payload.get("BillRefNumber", "")
    amount = _money(payload.get("TransAmount"))
    shortcode = str(
        payload.get("BusinessShortCode") or ""
    ).strip()

    if not _is_configured_shortcode(shortcode):
        return JsonResponse({
            "ResultCode": "C2B00015",
            "ResultDesc": "Invalid ShortCode",
        })

    if amount <= 0:
        return JsonResponse({
            "ResultCode": "C2B00013",
            "ResultDesc": "Invalid Amount",
        })

    till = _configured_till_number()
    till_shortcode = _configured_till_shortcode()

    paybill = str(
        getattr(settings, "ALTERNATE_MPESA_PAYBILL", "") or ""
    ).strip()

    # Till payments do not necessarily carry BillRefNumber.
    if shortcode in {till, till_shortcode}:
        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Accepted",
        })

    student = _student_from_reference(reference)

    if not student:
        return JsonResponse({
            "ResultCode": "C2B00012",
            "ResultDesc": "Invalid Account Number",
        })

    balance = _student_balance(student)

    if balance <= 0:
        return JsonResponse({
            "ResultCode": "C2B00013",
            "ResultDesc": "No outstanding fee balance",
        })

    if amount > balance:
        return JsonResponse({
            "ResultCode": "C2B00013",
            "ResultDesc": "Payment exceeds outstanding balance",
        })

    return JsonResponse({
        "ResultCode": "0",
        "ResultDesc": "Accepted",
    })


@csrf_exempt
@require_POST
def alternate_c2b_confirmation(request):
    """
    Automatic C2B confirmation.

    Handles:
    - PayBill payments using BillRefNumber
    - Till payments using a pending TillPaymentIntent
    """

    try:
        payload = json.loads(
            request.body.decode("utf-8") or "{}"
        )
    except Exception:
        return JsonResponse({
            "ResultCode": "C2B00011",
            "ResultDesc": "Invalid JSON",
        })

    logger.info(
        "ALTERNATE C2B CALLBACK: %s",
        json.dumps(
            payload,
            ensure_ascii=False
        ),
    )

    transaction_id = str(
        payload.get("TransID") or ""
    ).strip()

    reference = str(
        payload.get("BillRefNumber") or ""
    ).strip()

    amount = _money(
        payload.get("TransAmount")
    )

    msisdn = _normalise_phone(
        payload.get("MSISDN")
    )

    trans_time = str(
        payload.get("TransTime") or ""
    ).strip()

    shortcode = str(
        payload.get("BusinessShortCode") or ""
    ).strip()

    till = _configured_till_number()
    till_shortcode = _configured_till_shortcode()

    if not transaction_id or amount <= 0:
        return JsonResponse({
            "ResultCode": "C2B00011",
            "ResultDesc": "Missing transaction information",
        })

    # --------------------------------------------------------
    # GLOBAL IDEMPOTENCY
    # --------------------------------------------------------

    if FeePayment.objects.filter(
        receipt_number=transaction_id
    ).exists():

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Already processed",
        })

    if TillPaymentIntent.objects.filter(
        transaction_id=transaction_id
    ).exists():

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Already processed",
        })

    # --------------------------------------------------------
    # TILL AUTOMATIC MATCHING
    # --------------------------------------------------------

    is_till = (
        shortcode in {till, till_shortcode}
        or (
            not shortcode
            and bool(till)
        )
    )

    if is_till:

        if not msisdn:
            logger.warning(
                "TILL C2B %s has no MSISDN",
                transaction_id,
            )

            return JsonResponse({
                "ResultCode": "0",
                "ResultDesc": "Received for reconciliation",
            })

        candidates = list(
            TillPaymentIntent.objects
            .select_for_update()
            .filter(
                phone_number=msisdn,
                amount=amount,
                status="PENDING",
            )
            .order_by("-created_at")[:5]
        )

        if len(candidates) != 1:

            logger.warning(
                "TILL C2B unmatched/ambiguous: "
                "TX=%s PHONE=%s AMOUNT=%s CANDIDATES=%s",
                transaction_id,
                msisdn,
                amount,
                len(candidates),
            )

            return JsonResponse({
                "ResultCode": "0",
                "ResultDesc": "Received for reconciliation",
            })

        intent = candidates[0]
        student = intent.student

        balance = _student_balance(student)

        if balance <= 0:
            intent.status = "UNMATCHED"
            intent.notes = (
                "Payment received after learner balance "
                "was already cleared."
            )
            intent.save(
                update_fields=["status", "notes"]
            )

            return JsonResponse({
                "ResultCode": "0",
                "ResultDesc": "Received",
            })

        if amount > balance:
            intent.status = "UNMATCHED"
            intent.notes = (
                "Received amount exceeds outstanding balance."
            )
            intent.save(
                update_fields=["status", "notes"]
            )

            return JsonResponse({
                "ResultCode": "0",
                "ResultDesc": "Received for reconciliation",
            })

        try:
            with transaction.atomic():

                created = _allocate_payment(
                    student,
                    amount,
                    transaction_id,
                )

                if created:

                    intent.status = "VERIFIED"
                    intent.transaction_id = transaction_id
                    intent.transaction_time = trans_time
                    intent.verified_at = timezone.now()
                    intent.notes = (
                        "Automatically verified from M-Pesa Till."
                    )

                    intent.save(
                        update_fields=[
                            "status",
                            "transaction_id",
                            "transaction_time",
                            "verified_at",
                            "notes",
                        ]
                    )

                    logger.info(
                        "TILL PAYMENT VERIFIED: "
                        "TX=%s STUDENT=%s AMOUNT=%s PHONE=%s",
                        transaction_id,
                        student.admission_no,
                        amount,
                        msisdn,
                    )

        except Exception:
            logger.exception(
                "TILL C2B processing failure: %s",
                transaction_id,
            )

            return JsonResponse({
                "ResultCode": "0",
                "ResultDesc": "Received",
            })

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Accepted",
        })

    # --------------------------------------------------------
    # EXISTING PAYBILL FLOW
    # --------------------------------------------------------

    student = _student_from_reference(reference)

    if not student:

        logger.warning(
            "C2B unmatched admission/reference '%s'",
            reference,
        )

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Received for reconciliation",
        })

    balance = _student_balance(student)

    if balance <= 0:
        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Received",
        })

    if amount > balance:
        logger.warning(
            "C2B payment exceeds balance: "
            "%s / %s",
            amount,
            balance,
        )

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Received for reconciliation",
        })

    try:

        with transaction.atomic():

            created = _allocate_payment(
                student,
                amount,
                transaction_id,
            )

            if created:

                logger.info(
                    "C2B VERIFIED: %s | %s | KES %s | %s",
                    transaction_id,
                    student.admission_no,
                    amount,
                    msisdn,
                )

    except Exception:
        logger.exception(
            "C2B processing failure: %s",
            transaction_id,
        )

        return JsonResponse({
            "ResultCode": "0",
            "ResultDesc": "Received",
        })

    return JsonResponse({
        "ResultCode": "0",
        "ResultDesc": "Accepted",
    })


@csrf_exempt
@require_POST
def alternate_c2b_callback(request):
    return alternate_c2b_confirmation(request)


# ============================================================
# AUTOMATIC TILL PAYMENT PAGE
# ============================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import AlternatePaymentSettings, AutomaticPaymentSettings
from .payment_method_access import require_automatic_payment
from .services.online_payments import OnlinePaymentError


def _till_student(request, admission_no):
    admission_no = str(admission_no or "").strip()

    if not admission_no:
        raise OnlinePaymentError(
            "Enter the learner admission number."
        )

    student = (
        Student.objects
        .filter(admission_no__iexact=admission_no)
        .first()
    )

    if not student:
        raise OnlinePaymentError(
            "Learner with that admission number was not found."
        )

    profile = getattr(request.user, "profile", None)
    role = str(
        getattr(profile, "role", "") or ""
    ).upper()

    if request.user.is_superuser or role in (
        "ADMIN",
        "SUPERADMIN",
        "DIRECTOR",
        "STAFF",
    ):
        return student

    if role == "STUDENT":
        linked = getattr(profile, "student", None)

        if not linked or linked.pk != student.pk:
            raise OnlinePaymentError(
                "You are not authorised to pay for this learner."
            )

    elif role == "PARENT":
        parent = getattr(request.user, "parent", None)

        if not parent or not parent.children.filter(
            pk=student.pk
        ).exists():
            raise OnlinePaymentError(
                "You are not authorised to pay for this learner."
            )

    else:
        raise OnlinePaymentError(
            "You are not authorised to make this payment."
        )

    return student


def _till_phone(value):
    value = str(value or "").strip()

    digits = "".join(
        c for c in value
        if c.isdigit()
    )

    if digits.startswith("254"):
        return digits

    if digits.startswith("0"):
        return "254" + digits[1:]

    if digits.startswith("7") or digits.startswith("1"):
        return "254" + digits

    return digits


@login_required
def alternate_till_payment(request):

    # Enforce administrator enable/disable setting server-side.
    # This protects both GET and POST access from the portal.
    try:
        require_automatic_payment("MPESA_TILL")
    except RuntimeError as exc:
        return render(
            request,
            "fees/alternate_till_payment.html",
            {
                "error": str(exc),
                "admission_no": (
                    request.POST.get("admission_no")
                    or request.GET.get("admission_no")
                    or ""
                ).strip(),
                "student": None,
                "balance": Decimal("0.00"),
                "till": "",
                "phone_number": "",
                "amount": "",
            },
            status=403,
        )

    from .services.online_payments import create_online_payment
    from .services.mpesa import initiate_stk_push
    from .services.automatic_mpesa import initiate_automatic_stk_push

    admission_no = str(
        request.POST.get("admission_no")
        or request.GET.get("admission_no")
        or ""
    ).strip()

    try:
        student = _till_student(request, admission_no)

        records = (
            FeeRecord.objects
            .filter(
                student=student,
                term__is_closed=False,
            )
            .order_by("id")
        )

        balance = Decimal("0.00")
        payable_record = None

        for record in records:
            record_balance = _money(record.balance)

            if record_balance > 0 and payable_record is None:
                payable_record = record

            balance += record_balance

        if balance <= 0:
            raise OnlinePaymentError(
                "This learner has no outstanding fee balance."
            )

        # ----------------------------------------------------
        # Till receiving account comes from the new automatic
        # payment settings. Legacy AlternatePaymentSettings
        # and .env are only fallbacks.
        # ----------------------------------------------------

        automatic_settings = (
            AutomaticPaymentSettings.objects
            .filter(pk=1)
            .first()
        )

        till = ""

        if automatic_settings:
            till = str(
                automatic_settings.mpesa_till_number or ""
            ).strip()

        if not till:
            settings_obj = (
                AlternatePaymentSettings.objects
                .filter(pk=1)
                .first()
            )

            if settings_obj:
                till = str(
                    settings_obj.till_number or ""
                ).strip()

        if not till:
            till = str(
                getattr(
                    settings,
                    "ALTERNATE_MPESA_TILL",
                    "",
                )
                or ""
            ).strip()

        if not till:
            raise OnlinePaymentError(
                "M-Pesa Till is not configured."
            )

        if request.method == "GET":
            phone = _till_phone(
                getattr(student, "parent_phone", "")
            )

            return render(
                request,
                "fees/alternate_till_payment.html",
                {
                    "student": student,
                    "admission_no": admission_no,
                    "balance": balance,
                    "till": till,
                    "phone_number": phone,
                },
            )

        phone = _till_phone(
            request.POST.get("phone_number")
        )

        if len(phone) < 10:
            raise OnlinePaymentError(
                "Enter a valid M-Pesa phone number."
            )

        try:
            amount = _money(
                request.POST.get("amount")
            )
        except Exception:
            raise OnlinePaymentError(
                "Enter a valid payment amount."
            )

        if amount <= 0:
            raise OnlinePaymentError(
                "Payment amount must be greater than zero."
            )

        if amount > balance:
            raise OnlinePaymentError(
                "Payment amount cannot exceed the outstanding balance."
            )

        if payable_record is None:
            raise OnlinePaymentError(
                "No outstanding fee record was found."
            )

        record_balance = _money(payable_record.balance)

        if amount > record_balance:
            raise OnlinePaymentError(
                "The amount exceeds the outstanding balance "
                "of the selected fee record."
            )

        profile = getattr(request.user, "profile", None)
        role = str(
            getattr(profile, "role", "") or ""
        ).upper()

        if (
            request.user.is_superuser
            or role in {
                "ADMIN",
                "SUPERADMIN",
                "DIRECTOR",
                "STAFF",
            }
        ):
            payer_role = "ADMIN"
        elif role == "PARENT":
            payer_role = "PARENT"
        elif role == "STUDENT":
            payer_role = "STUDENT"
        else:
            raise OnlinePaymentError(
                "You are not authorised to make this payment."
            )

        # ---------------------------------------------------------
        # ALWAYS CREATE A NEW REQUEST
        # ---------------------------------------------------------
        # We deliberately do NOT reuse an old pending Till intent.
        # This prevents a stale STK request from blocking new prompts.
        # ---------------------------------------------------------

        online_payment = create_online_payment(
            payer=request.user,
            payer_role=payer_role,
            student=student,
            fee_record_id=payable_record.id,
            amount=amount,
            payment_method_code="MPESA",
            phone_number=phone,
        )

        # ---------------------------------------------------------
        # STK PUSH
        # ---------------------------------------------------------

        try:
            stk_result = initiate_automatic_stk_push(
                phone_number=phone,
                amount=amount,
                method="MPESA_TILL",
                account_reference=(
                    student.admission_no
                    or "SCHOOLFEES"
                ),
                transaction_desc="School Fees - M-Pesa Till",
            )
        except Exception as exc:
            online_payment.status = "FAILED"

            if hasattr(
                online_payment,
                "verification_message",
            ):
                online_payment.verification_message = str(exc)
                online_payment.save(
                    update_fields=[
                        "status",
                        "verification_message",
                        "updated_at",
                    ]
                )
            else:
                online_payment.save(
                    update_fields=["status"]
                )

            raise OnlinePaymentError(
                f"Unable to send the STK Push: {exc}"
            )

        # ---------------------------------------------------------
        # SAVE THE COMPLETE DARaja RESPONSE
        # ---------------------------------------------------------

        if not isinstance(stk_result, dict):
            online_payment.status = "FAILED"
            online_payment.verification_message = (
                "M-Pesa returned an invalid STK response."
            )
            online_payment.save(
                update_fields=[
                    "status",
                    "verification_message",
                    "updated_at",
                ]
            )

            raise OnlinePaymentError(
                "M-Pesa returned an invalid STK response."
            )

        merchant_request_id = str(
            stk_result.get("MerchantRequestID")
            or stk_result.get("merchant_request_id")
            or ""
        ).strip()

        checkout_request_id = str(
            stk_result.get("CheckoutRequestID")
            or stk_result.get("checkout_request_id")
            or ""
        ).strip()

        response_code = str(
            stk_result.get("ResponseCode")
            or stk_result.get("response_code")
            or ""
        ).strip()

        response_description = str(
            stk_result.get("ResponseDescription")
            or stk_result.get("response_description")
            or stk_result.get("CustomerMessage")
            or ""
        ).strip()

        online_payment.merchant_request_id = merchant_request_id
        online_payment.checkout_request_id = checkout_request_id
        online_payment.status = (
            "PROCESSING"
            if response_code == "0" and checkout_request_id
            else "FAILED"
        )

        if hasattr(
            online_payment,
            "provider_response_code",
        ):
            online_payment.provider_response_code = response_code

        if hasattr(
            online_payment,
            "provider_response_description",
        ):
            online_payment.provider_response_description = (
                response_description
            )

        if hasattr(
            online_payment,
            "provider_raw_response",
        ):
            online_payment.provider_raw_response = stk_result

        if hasattr(
            online_payment,
            "verification_message",
        ):
            online_payment.verification_message = (
                response_description
                or "M-Pesa STK request processed."
            )

        update_fields = [
            "merchant_request_id",
            "checkout_request_id",
            "status",
            "updated_at",
        ]

        for field_name in [
            "provider_response_code",
            "provider_response_description",
            "provider_raw_response",
            "verification_message",
        ]:
            if hasattr(online_payment, field_name):
                update_fields.append(field_name)

        online_payment.save(
            update_fields=update_fields
        )

        if not checkout_request_id:
            raise OnlinePaymentError(
                response_description
                or "M-Pesa did not return a CheckoutRequestID."
            )

        if response_code != "0":
            raise OnlinePaymentError(
                response_description
                or "M-Pesa STK request was not accepted."
            )

        # ---------------------------------------------------------
        # CREATE TILL INTENT
        # ---------------------------------------------------------

        intent = TillPaymentIntent.objects.create(
            student=student,
            amount=amount,
            phone_number=phone,
            till_number=till,
            status="PENDING",
            notes=(
                "STK Push sent successfully. "
                f"CheckoutRequestID={checkout_request_id}"
            ),
            online_payment=online_payment,
        )

        return render(
            request,
            "fees/alternate_till_payment.html",
            {
                "student": student,
                "admission_no": admission_no,
                "balance": balance,
                "amount": amount,
                "phone_number": phone,
                "till": till,
                "intent": intent,
                "online_payment": online_payment,
            },
        )

    except OnlinePaymentError as exc:
        return render(
            request,
            "fees/alternate_till_payment.html",
            {
                "error": str(exc),
                "admission_no": admission_no,
                "student": locals().get("student"),
                "balance": locals().get(
                    "balance",
                    Decimal("0.00"),
                ),
                "till": locals().get("till", ""),
                "phone_number": locals().get("phone", ""),
                "amount": locals().get("amount", ""),
            },
            status=400,
        )

@login_required
def alternate_till_payment_status(request, intent_id):

    intent = get_object_or_404(
        TillPaymentIntent.objects.select_related(
            "student",
            "online_payment",
            "online_payment__fee_payment",
        ),
        id=intent_id,
    )

    # Enforce the same learner ownership rules used when
    # creating the Till payment.
    _till_student(
        request,
        intent.student.admission_no,
    )

    online_payment = intent.online_payment

    # ------------------------------------------------------------
    # AUTOMATIC SYNCHRONIZATION
    # ------------------------------------------------------------

    if (
        online_payment
        and online_payment.status == "VERIFIED"
        and intent.status != "VERIFIED"
    ):
        intent.status = "VERIFIED"

        if not intent.transaction_id:
            intent.transaction_id = (
                online_payment.provider_receipt
                or online_payment.transaction_reference
                or ""
            )

        intent.verified_at = (
            intent.verified_at
            or timezone.now()
        )

        intent.notes = (
            "Till payment automatically verified. "
            "Official fee payment created."
        )

        intent.save(
            update_fields=[
                "status",
                "transaction_id",
                "verified_at",
                "notes",
            ]
        )

        intent.refresh_from_db()

    # ------------------------------------------------------------
    # CURRENT STATUS
    # ------------------------------------------------------------

    status = intent.status

    receipt_number = ""

    if online_payment:
        receipt_number = (
            online_payment.provider_receipt
            or online_payment.transaction_reference
            or ""
        )

        if (
            not receipt_number
            and online_payment.fee_payment_id
        ):
            receipt_number = (
                online_payment.fee_payment.receipt_number
                or ""
            )

    # ------------------------------------------------------------
    # CURRENT OUTSTANDING BALANCE
    # ------------------------------------------------------------

    balance = Decimal("0.00")

    try:
        records = (
            FeeRecord.objects
            .filter(
                student=intent.student,
                term__is_closed=False,
            )
        )

        for record in records:
            balance += _money(record.balance)

    except Exception:
        balance = Decimal("0.00")

    if status == "VERIFIED":
        message = (
            "Payment verified successfully. "
            "Official fee payment created."
        )

    elif status == "FAILED":
        message = (
            getattr(
                online_payment,
                "verification_message",
                "",
            )
            or "The M-Pesa payment was not completed."
        )

    elif status == "CANCELLED":
        message = "The payment was cancelled."

    elif status == "EXPIRED":
        message = "The payment request has expired."

    elif status == "UNMATCHED":
        message = "The payment could not be matched automatically."

    else:
        message = (
            "STK Push sent. Waiting for M-Pesa confirmation..."
        )

    return JsonResponse(
        {
            "ok": True,
            "status": status,
            "message": message,
            "transaction_id": (
                intent.transaction_id
                or receipt_number
                or ""
            ),
            "receipt_number": receipt_number,
            "receipt_url": (
                f"/fees/online/receipt/{online_payment.id}/pdf/"
                if online_payment and online_payment.status == "VERIFIED"
                else ""
            ),
            "balance": f"{balance:.2f}",
            "intent_id": intent.id,
            "online_payment_id": (
                online_payment.id
                if online_payment
                else None
            ),
        }
    )
