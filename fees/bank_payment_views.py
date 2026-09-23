
import json
import hmac
import hashlib
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    AutomaticPaymentSettings,
    BankTransaction,
)
from .bank_service import (
    verify_bank_transaction,
    fetch_bank_transactions,
    import_bank_api_response,
    get_fee_record,
)
from students.models import Student
from .payment_method_access import require_automatic_payment
from .alternate_payment_auto import _payer_role, _authorized_student
from accounts.staff_access import role_permission_required
from .bank_integration_engine import fetch_transactions_from_configured_bank, get_bank_profile, get_bank_integration_status, required_configuration


def _is_admin(request):

    profile = getattr(
        request.user,
        "profile",
        None,
    )

    role = (
        getattr(profile, "role", "")
        .upper()
        if profile
        else ""
    )

    return (
        request.user.is_superuser
        or role in [
            "ADMIN",
            "SUPERADMIN",
            "DIRECTOR",
        ]
    )


@login_required
def bank_payment_page(request):
    """
    Parent/student bank payment instructions.

    This page NEVER creates a fake BankTransaction.
    A BankTransaction is created only after the real bank transaction
    arrives through the configured bank API/webhook.
    """
    payer_role = _payer_role(request)

    if payer_role not in {"ADMIN", "PARENT", "STUDENT"}:
        messages.error(
            request,
            "Your account is not authorized to make bank payments.",
        )
        return redirect("accounts:login")

    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    disabled = (
        not settings
        or not settings.is_active
        or not settings.bank_enabled
    )

    admission_no = (
        request.POST.get("admission_no")
        if request.method == "POST"
        else request.GET.get("admission_no")
    )

    admission_no = (admission_no or "").strip().upper()

    student = None
    fee_record = None
    reference = None
    amount = None
    error = None

    if not disabled and admission_no:
        student = _authorized_student(
            request,
            admission_no,
        )

        if student:
            fee_record = get_fee_record(student)

            if settings.bank_reference_mode == "MANUAL":
                reference = (
                    settings.bank_manual_reference
                    or f"{settings.bank_reference_prefix}{student.admission_no}"
                )

            elif settings.bank_reference_mode == "ACCOUNT":
                reference = (
                    f"{settings.bank_reference_prefix}"
                    f"{student.admission_no}"
                )

            else:
                reference = (
                    f"{settings.bank_reference_prefix}"
                    f"{student.admission_no}"
                )

            if request.method == "POST":
                raw_amount = (request.POST.get("amount") or "").strip()

                if raw_amount:
                    try:
                        amount = Decimal(raw_amount)

                        if amount <= 0:
                            error = "Enter a valid payment amount."

                        elif settings.bank_minimum_payment and (
                            amount < settings.bank_minimum_payment
                        ):
                            error = (
                                f"Minimum bank payment is "
                                f"{settings.bank_minimum_payment}."
                            )

                        elif settings.bank_maximum_payment and (
                            amount > settings.bank_maximum_payment
                        ):
                            error = (
                                f"Maximum bank payment is "
                                f"{settings.bank_maximum_payment}."
                            )

                        elif fee_record and amount > fee_record.balance:
                            error = (
                                f"Payment cannot exceed the outstanding balance "
                                f"of {fee_record.balance}."
                            )

                    except Exception:
                        error = "Enter a valid numeric payment amount."
                else:
                    error = "Enter the amount you intend to pay."

    return render(
        request,
        "fees/bank_payment.html",
        {
            "settings": settings,
            "disabled": disabled,
            "admission_no": admission_no,
            "student": student,
            "fee_record": fee_record,
            "reference": reference,
            "amount": amount,
            "error": error,
        },
    )



@login_required
@role_permission_required("change_automaticpaymentsettings", "fees")
def bank_connection_test(request):
    """
    Tests the configured bank transaction integration without
    creating FeePayments.

    A successful test only proves that the configured bank
    endpoint/authentication responded successfully. It does not
    mark any learner payment as paid.
    """
    from django.contrib import messages

    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings:
        messages.error(
            request,
            "Bank automatic payment settings have not been configured."
        )
        return redirect("fees:bank_settings")

    if not settings.is_active:
        messages.error(
            request,
            "Automatic payments are disabled. Enable them first."
        )
        return redirect("fees:bank_settings")

    if not settings.bank_enabled:
        messages.error(
            request,
            "Bank automatic verification is disabled. Enable Bank first."
        )
        return redirect("fees:bank_settings")

    required = []

    if not settings.bank_name:
        required.append("Bank name")

    if not settings.bank_account_number:
        required.append("Bank account number")

    if not settings.bank_transaction_endpoint:
        required.append("Transaction Endpoint")

    auth_method = (
        getattr(settings, "bank_authentication_method", "") or ""
    ).upper()

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

    if required:
        settings.bank_verification_status = (
            "NOT CONFIGURED: " + ", ".join(required)[:180]
        )
        settings.save(update_fields=["bank_verification_status"])

        messages.error(
            request,
            "Bank integration is incomplete: " + ", ".join(required)
        )
        return redirect("fees:bank_settings")

    try:
        integration_result = fetch_transactions_from_configured_bank(
            settings
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
            transaction_count = len(possible) if isinstance(possible, list) else 0
        else:
            transaction_count = 0

        settings.bank_verification_status = (
            "CONNECTION OK - "
            + integration_result.get("bank", "Bank")
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
            f"{integration_result.get('bank', 'Bank')} transaction service responded. "
            f"{transaction_count} transaction(s) returned."
        )

    except Exception as exc:
        error_text = str(exc).replace("\n", " ").strip()

        settings.bank_verification_status = (
            "CONNECTION FAILED: " + error_text[:180]
        )
        settings.save(update_fields=["bank_verification_status"])

        messages.error(
            request,
            "Bank connection test failed: " + error_text[:500]
        )

    return redirect("fees:bank_settings")

@login_required
def bank_self_service_verify(request):
    """
    Self-service bank transaction verification.

    The user enters the transaction code supplied by the bank.
    The ERP only succeeds when that transaction already exists in
    BankTransaction and can be verified against the configured rules.
    """
    settings = AutomaticPaymentSettings.objects.filter(pk=1).first()

    if not settings or not settings.is_active or not settings.bank_enabled:
        return render(
            request,
            "fees/bank_self_service_verify.html",
            {
                "disabled": True,
                "settings": settings,
            },
        )

    transaction_code = ""

    if request.method == "POST":
        transaction_code = (
            request.POST.get("transaction_code") or ""
        ).strip().upper()

        if not transaction_code:
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": "Enter the bank transaction code.",
                    "transaction_code": transaction_code,
                },
            )

        bank_transaction = (
            BankTransaction.objects
            .select_related("student", "fee_record", "fee_payment")
            .filter(transaction_id__iexact=transaction_code)
            .first()
        )

        if not bank_transaction:
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": (
                        "Transaction code not found. "
                        "Please confirm the code and try again. "
                        "The bank transaction must first be received by "
                        "the school's bank integration."
                    ),
                    "transaction_code": transaction_code,
                },
            )

        authorized_student = _authorized_student(
            request,
            bank_transaction.student.admission_no,
        )

        if authorized_student is None:
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": (
                        "You are not authorized to verify this "
                        "learner's bank transaction."
                    ),
                    "transaction_code": transaction_code,
                },
                status=403,
            )

        try:
            verified_transaction = verify_bank_transaction(
                bank_transaction.id
            )
        except Exception as exc:
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": str(exc),
                    "transaction_code": transaction_code,
                    "bank_transaction": bank_transaction,
                },
            )

        bank_transaction.refresh_from_db()

        if bank_transaction.status != "VERIFIED":
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": (
                        bank_transaction.verification_message
                        or "The bank transaction could not be verified."
                    ),
                    "transaction_code": transaction_code,
                    "bank_transaction": bank_transaction,
                },
            )

        if not bank_transaction.fee_payment_id:
            return render(
                request,
                "fees/bank_self_service_verify.html",
                {
                    "settings": settings,
                    "error": (
                        "Transaction was verified but no official fee "
                        "payment was created. Please contact the school."
                    ),
                    "transaction_code": transaction_code,
                    "bank_transaction": bank_transaction,
                },
            )

        return render(
            request,
            "fees/bank_self_service_verify.html",
            {
                "settings": settings,
                "success": True,
                "transaction_code": transaction_code,
                "bank_transaction": bank_transaction,
                "fee_payment": bank_transaction.fee_payment,
                "student": bank_transaction.student,
            },
        )

    return render(
        request,
        "fees/bank_self_service_verify.html",
        {
            "settings": settings,
            "transaction_code": transaction_code,
        },
    )

@login_required
@role_permission_required("view_banktransaction", "fees")
def bank_transactions(request):

    status = request.GET.get("status", "").strip()

    qs = (
        BankTransaction.objects
        .select_related(
            "student",
            "fee_record",
            "fee_payment",
        )
    )

    if status:
        qs = qs.filter(status=status)

    return render(
        request,
        "fees/bank_transactions.html",
        {
            "transactions": qs[:500],
            "selected_status": status,
        },
    )


@login_required
@role_permission_required("change_banktransaction", "fees")
def bank_transaction_verify(request, transaction_id):

    if request.method != "POST":
        return redirect("fees:bank_transactions")

    tx = get_object_or_404(
        BankTransaction,
        pk=transaction_id,
    )

    try:
        verify_bank_transaction(tx.pk)
        messages.success(
            request,
            "Bank transaction verification completed.",
        )
    except Exception as exc:
        messages.error(
            request,
            f"Verification failed: {exc}",
        )

    return redirect("fees:bank_transactions")


@login_required
@role_permission_required("change_banktransaction", "fees")
def bank_transaction_assign(request, transaction_id):

    if request.method != "POST":
        return redirect("fees:bank_transactions")

    tx = get_object_or_404(
        BankTransaction,
        pk=transaction_id,
    )

    admission_no = (
        request.POST.get("admission_no")
        or ""
    ).strip()

    student = (
        Student.objects
        .filter(
            admission_no__iexact=admission_no,
            is_active=True,
        )
        .first()
    )

    if not student:
        messages.error(
            request,
            "Student admission number was not found.",
        )
        return redirect(
            "fees:bank_transactions"
        )

    tx.student = student
    tx.status = "PENDING"
    tx.verification_message = (
        "Student manually assigned by administrator."
    )
    tx.save()

    try:
        verify_bank_transaction(tx.pk)
        messages.success(
            request,
            "Transaction assigned and verification attempted.",
        )
    except Exception as exc:
        messages.error(
            request,
            f"Verification failed: {exc}",
        )

    return redirect("fees:bank_transactions")


@login_required
@role_permission_required("change_banktransaction", "fees")
def bank_sync_now(request):

    if request.method != "POST":
        return redirect("fees:bank_transactions")

    try:
        require_automatic_payment("BANK")

        payload = fetch_bank_transactions()

        imported = import_bank_api_response(
            payload
        )

        settings = (
            AutomaticPaymentSettings.objects
            .filter(pk=1)
            .first()
        )

        if settings:
            settings.bank_last_sync = timezone.now()
            settings.bank_verification_status = (
                "CONNECTED"
            )
            settings.save(
                update_fields=[
                    "bank_last_sync",
                    "bank_verification_status",
                    "updated_at",
                ]
            )

        messages.success(
            request,
            f"Bank synchronization completed. "
            f"{len(imported)} new transaction(s) imported.",
        )

    except Exception as exc:

        settings = (
            AutomaticPaymentSettings.objects
            .filter(pk=1)
            .first()
        )

        if settings:
            settings.bank_verification_status = (
                "ERROR"
            )
            settings.save(
                update_fields=[
                    "bank_verification_status",
                    "updated_at",
                ]
            )

        messages.error(
            request,
            f"Bank synchronization failed: {exc}",
        )

    return redirect("fees:bank_transactions")


def bank_webhook(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "ok": False,
                "error": "POST required",
            },
            status=405,
        )

    settings = (
        AutomaticPaymentSettings.objects
        .filter(pk=1)
        .first()
    )

    if not settings or not settings.bank_enabled:
        return JsonResponse(
            {
                "ok": False,
                "error": "Bank payments disabled",
            },
            status=403,
        )

    raw = request.body

    configured_secret = (
        settings.bank_webhook_secret or ""
    ).strip()

    supplied_secret = (
        request.headers.get("X-Bank-Webhook-Secret")
        or request.headers.get("X-Webhook-Secret")
        or ""
    )

    signature = (
        request.headers.get("X-Bank-Signature")
        or ""
    )

    if configured_secret:

        valid = False

        if supplied_secret:
            valid = hmac.compare_digest(
                supplied_secret,
                configured_secret,
            )

        elif signature:

            expected = hmac.new(
                configured_secret.encode(),
                raw,
                hashlib.sha256,
            ).hexdigest()

            valid = hmac.compare_digest(
                signature,
                expected,
            )

        if not valid:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Invalid webhook authentication",
                },
                status=401,
            )

    try:
        payload = json.loads(
            raw.decode("utf-8")
        )
    except Exception:
        return JsonResponse(
            {
                "ok": False,
                "error": "Invalid JSON",
            },
            status=400,
        )

    item = payload

    if isinstance(payload, dict):

        if isinstance(
            payload.get("transaction"),
            dict,
        ):
            item = payload["transaction"]

        elif isinstance(
            payload.get("data"),
            dict,
        ):
            item = payload["data"]

    transaction_id = (
        item.get("transaction_id")
        or item.get("transactionId")
        or item.get("referenceNumber")
        or item.get("receipt")
        or item.get("id")
    )

    amount = (
        item.get("amount")
        or item.get("transactionAmount")
        or item.get("creditAmount")
    )

    reference = (
        item.get("reference")
        or item.get("accountReference")
        or item.get("narration")
        or item.get("description")
        or ""
    )

    if not transaction_id or amount is None:
        return JsonResponse(
            {
                "ok": False,
                "error": "Transaction ID and amount are required",
            },
            status=400,
        )

    try:
        amount = Decimal(str(amount))
    except Exception:
        return JsonResponse(
            {
                "ok": False,
                "error": "Invalid amount",
            },
            status=400,
        )

    tx, created = (
        BankTransaction.objects.get_or_create(
            transaction_id=str(transaction_id),
            defaults={
                "amount": amount,
                "reference": str(reference),
                "payer_name": str(
                    item.get("payerName")
                    or item.get("customerName")
                    or item.get("name")
                    or ""
                ),
                "payer_account": str(
                    item.get("accountNumber")
                    or item.get("account_number")
                    or ""
                ),
                "bank_name": str(
                    item.get("bankName")
                    or config.bank_name
                    or ""
                ),
                "bank_account_number": str(
                    item.get("creditAccount")
                    or config.bank_account_number
                    or ""
                ),
                "currency": str(
                    item.get("currency")
                    or item.get("currencyCode")
                    or "KES"
                ),
                "status": "PENDING",
                "raw_payload": payload,
            },
        )
    )

    if created:
        try:
            verify_bank_transaction(tx.pk)
        except Exception as exc:
            tx.status = "ERROR"
            tx.verification_message = str(exc)
            tx.save()

    return JsonResponse(
        {
            "ok": True,
            "created": created,
            "transaction_id": tx.transaction_id,
            "status": tx.status,
            "receipt_number": (
                tx.fee_payment.receipt_number
                if tx.fee_payment
                else ""
            ),
        }
    )

