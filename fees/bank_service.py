
from decimal import Decimal, InvalidOperation
from datetime import datetime
import base64
import json
import urllib.request
import urllib.parse
import urllib.error

from django.db import transaction
from django.utils import timezone

from .models import (
    AutomaticPaymentSettings,
    BankTransaction,
    FeePayment,
    FeeRecord,
)
from students.models import Student


def normalize_reference(value):
    return "".join(
        str(value or "").strip().upper().split()
    )


def extract_reference(settings, reference):
    reference = normalize_reference(reference)

    prefix = normalize_reference(
        settings.bank_reference_prefix
    )

    if prefix and reference.startswith(prefix):
        reference = reference[len(prefix):]

    return reference


def find_student_by_reference(settings, reference):

    ref = extract_reference(settings, reference)

    if not ref:
        return None

    student = Student.objects.filter(
        admission_no__iexact=ref
    ).first()

    return student


def get_fee_record(student):

    return (
        FeeRecord.objects
        .filter(student=student)
        .order_by("-id")
        .first()
    )


@transaction.atomic
def verify_bank_transaction(bank_transaction_id):

    settings = (
        AutomaticPaymentSettings.objects
        .select_for_update()
        .filter(pk=1)
        .first()
    )

    tx = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "student",
            "fee_record",
            "fee_payment",
        )
        .get(pk=bank_transaction_id)
    )

    if tx.status == "VERIFIED":
        return tx

    if settings and settings.bank_duplicate_protection:

        duplicate = (
            BankTransaction.objects
            .filter(
                transaction_id=tx.transaction_id,
                status="VERIFIED",
            )
            .exclude(pk=tx.pk)
            .first()
        )

        if duplicate:
            tx.status = "DUPLICATE"
            tx.verification_message = (
                "Duplicate bank transaction detected."
            )
            tx.save(
                update_fields=[
                    "status",
                    "verification_message",
                    "updated_at",
                ]
            )
            return tx

    if settings:

        minimum = settings.bank_minimum_payment
        maximum = settings.bank_maximum_payment

        if minimum is not None and tx.amount < minimum:
            tx.status = "REJECTED"
            tx.verification_message = (
                "Transaction is below the configured minimum amount."
            )
            tx.save()
            return tx

        if maximum is not None and tx.amount > maximum:
            tx.status = "REJECTED"
            tx.verification_message = (
                "Transaction exceeds the configured maximum amount."
            )
            tx.save()
            return tx

    if not tx.student:

        if settings:
            student = find_student_by_reference(
                settings,
                tx.reference,
            )
        else:
            student = None

        if student:
            tx.student = student
        else:
            tx.status = "UNMATCHED"
            tx.verification_message = (
                "No student matched the bank payment reference."
            )
            tx.save()
            return tx

    if not tx.fee_record:
        tx.fee_record = get_fee_record(tx.student)

    if not tx.fee_record:
        tx.status = "UNMATCHED"
        tx.verification_message = (
            "Student found, but no fee record exists."
        )
        tx.save()
        return tx

    fee_record = (
        FeeRecord.objects
        .select_for_update()
        .get(pk=tx.fee_record.pk)
    )

    try:
        balance = Decimal(str(fee_record.balance))
    except (InvalidOperation, TypeError):
        balance = Decimal("0")

    if tx.amount <= Decimal("0"):
        tx.status = "REJECTED"
        tx.verification_message = "Invalid transaction amount."
        tx.save()
        return tx

    if tx.amount > balance:
        tx.status = "REJECTED"
        tx.verification_message = (
            f"Payment exceeds outstanding balance of {balance}."
        )
        tx.save()
        return tx

    duplicate_receipt = (
        FeePayment.objects
        .filter(reference=tx.transaction_id)
        .first()
    )

    if duplicate_receipt:
        tx.status = "DUPLICATE"
        tx.fee_payment = duplicate_receipt
        tx.verification_message = (
            "A FeePayment already exists for this bank transaction."
        )
        tx.save()
        return tx

    payment = FeePayment(
        fee_record=fee_record,
        amount=tx.amount,
        payment_date=(
            tx.transaction_time.date()
            if tx.transaction_time
            else timezone.localdate()
        ),
        payment_method="Bank",
        reference=tx.transaction_id,
    )

    payment.save()

    tx.fee_payment = payment
    tx.status = "VERIFIED"
    tx.verified_at = timezone.now()
    tx.verification_message = (
        "Bank payment automatically verified and posted."
    )
    tx.save()

    return tx


def _json_request(url, method="GET", data=None, headers=None):

    headers = headers or {}

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers.setdefault(
            "Content-Type",
            "application/json",
        )

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:

        raw = response.read().decode("utf-8")

        if not raw:
            return {}

        return json.loads(raw)


def get_bank_access_token(settings):

    if not settings.bank_access_token_url:
        return ""

    auth_method = (
        settings.bank_authentication_method or ""
    ).lower()

    if "oauth" not in auth_method:
        return ""

    credentials = (
        f"{settings.bank_client_id}:"
        f"{settings.bank_client_secret}"
    )

    encoded = base64.b64encode(
        credentials.encode()
    ).decode()

    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
    }).encode()

    request = urllib.request.Request(
        settings.bank_access_token_url,
        data=body,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",
            "Authorization":
                f"Basic {encoded}",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    return (
        result.get("access_token")
        or result.get("token")
        or ""
    )


def fetch_bank_transactions():

    settings = (
        AutomaticPaymentSettings.objects
        .filter(pk=1)
        .first()
    )

    if not settings:
        raise RuntimeError(
            "Automatic Payment Settings do not exist."
        )

    if not settings.bank_enabled:
        raise RuntimeError(
            "Automatic Bank Payments are disabled."
        )

    if not settings.bank_transaction_endpoint:
        raise RuntimeError(
            "Bank transaction endpoint is not configured."
        )

    headers = {
        "Accept": "application/json",
    }

    auth_method = (
        settings.bank_authentication_method or ""
    ).lower()

    if "oauth" in auth_method:

        token = get_bank_access_token(settings)

        if token:
            headers["Authorization"] = (
                f"Bearer {token}"
            )

    elif "bearer" in auth_method:

        if settings.bank_api_key:
            headers["Authorization"] = (
                f"Bearer {settings.bank_api_key}"
            )

    elif "api key" in auth_method:

        if settings.bank_api_key:
            headers["X-API-Key"] = settings.bank_api_key

    elif "basic" in auth_method:

        credentials = (
            f"{settings.bank_client_id}:"
            f"{settings.bank_client_secret}"
        )

        encoded = base64.b64encode(
            credentials.encode()
        ).decode()

        headers["Authorization"] = (
            f"Basic {encoded}"
        )

    elif settings.bank_api_key:

        headers["X-API-Key"] = settings.bank_api_key

    return _json_request(
        settings.bank_transaction_endpoint,
        headers=headers,
    )


def import_bank_api_response(payload):

    if isinstance(payload, dict):

        transactions = (
            payload.get("transactions")
            or payload.get("data")
            or payload.get("results")
            or []
        )

    elif isinstance(payload, list):
        transactions = payload

    else:
        transactions = []

    imported = []

    for item in transactions:

        if not isinstance(item, dict):
            continue

        transaction_id = (
            item.get("transaction_id")
            or item.get("transactionId")
            or item.get("referenceNumber")
            or item.get("receipt")
            or item.get("id")
        )

        if not transaction_id:
            continue

        amount = (
            item.get("amount")
            or item.get("transactionAmount")
            or item.get("creditAmount")
            or 0
        )

        try:
            amount = Decimal(str(amount))
        except Exception:
            continue

        reference = (
            item.get("reference")
            or item.get("accountReference")
            or item.get("narration")
            or item.get("description")
            or ""
        )

        payer_name = (
            item.get("payer_name")
            or item.get("payerName")
            or item.get("customerName")
            or item.get("name")
            or ""
        )

        currency = (
            item.get("currency")
            or item.get("currencyCode")
            or "KES"
        )

        bank_account = (
            item.get("accountNumber")
            or item.get("account_number")
            or ""
        )

        bank_name = (
            item.get("bankName")
            or ""
        )

        tx, created = (
            BankTransaction.objects.get_or_create(
                transaction_id=str(transaction_id),
                defaults={
                    "amount": amount,
                    "reference": str(reference),
                    "payer_name": str(payer_name),
                    "currency": str(currency),
                    "payer_account": str(bank_account),
                    "bank_name": str(bank_name),
                    "status": "PENDING",
                    "raw_payload": item,
                },
            )
        )

        if created:
            verify_bank_transaction(tx.pk)
            imported.append(tx.pk)

    return imported
