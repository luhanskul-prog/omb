
import base64
import json
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    AutomaticPaymentSettings,
    MpesaPaybillTransaction,
    FeePayment,
)
from students.models import Student


def get_config():
    return AutomaticPaymentSettings.objects.filter(pk=1).first()


def _environment():
    config = get_config()

    value = (
        getattr(config, "environment", None)
        or getattr(settings, "MPESA_ENVIRONMENT", "sandbox")
        or "sandbox"
    )

    value = str(value).lower().strip()

    if value in ("production", "live", "prod"):
        return "production"

    return "sandbox"


def _base_url():
    if _environment() == "production":
        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


def _credentials():
    config = get_config()

    if not config:
        raise RuntimeError(
            "Automatic payment settings are not configured."
        )

    key = config.mpesa_paybill_consumer_key
    secret = config.mpesa_paybill_consumer_secret

    if not key or not secret:
        raise RuntimeError(
            "M-Pesa PayBill Consumer Key and Consumer Secret "
            "are not configured."
        )

    return key, secret


def get_access_token():
    key, secret = _credentials()

    auth = base64.b64encode(
        f"{key}:{secret}".encode()
    ).decode()

    response = requests.get(
        f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    token = data.get("access_token")

    if not token:
        raise RuntimeError(
            "Safaricom did not return an access token."
        )

    return token


def configured_shortcode():
    config = get_config()

    if not config:
        return ""

    return str(
        config.mpesa_paybill_shortcode
        or config.mpesa_paybill_number
        or ""
    ).strip()


def configured_validation_url():
    config = get_config()

    if not config:
        return ""

    return str(
        config.mpesa_paybill_validation_url or ""
    ).strip()


def configured_confirmation_url():
    config = get_config()

    if not config:
        return ""

    return str(
        config.mpesa_paybill_confirmation_url or ""
    ).strip()


def register_c2b_urls(
    validation_url=None,
    confirmation_url=None,
    response_type="Completed",
):
    config = get_config()

    if not config:
        raise RuntimeError(
            "Automatic payment settings are not configured."
        )

    shortcode = configured_shortcode()

    if not shortcode:
        raise RuntimeError(
            "M-Pesa PayBill Short Code/PayBill Number is not configured."
        )

    validation_url = (
        validation_url
        or configured_validation_url()
    )

    confirmation_url = (
        confirmation_url
        or configured_confirmation_url()
    )

    if not validation_url:
        raise RuntimeError(
            "Validation URL is not configured."
        )

    if not confirmation_url:
        raise RuntimeError(
            "Confirmation URL is not configured."
        )

    token = get_access_token()

    payload = {
        "ShortCode": shortcode,
        "ResponseType": response_type,
        "ConfirmationURL": confirmation_url,
        "ValidationURL": validation_url,
    }

    response = requests.post(
        f"{_base_url()}/mpesa/c2b/v2/registerurl",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        data = {
            "http_status": response.status_code,
            "raw": response.text,
        }

    if not response.ok:
        raise RuntimeError(
            f"Safaricom C2B URL registration failed: {data}"
        )

    return data


def normalize_reference(value):
    value = str(value or "").strip().upper()

    config = get_config()

    prefix = (
        str(
            getattr(
                config,
                "mpesa_paybill_account",
                "",
            )
            or ""
        )
        .strip()
        .upper()
    )

    # Do not blindly remove account numbers.
    # Admission number/reference is preserved exactly.
    return value


def find_student_from_reference(reference):
    reference = normalize_reference(reference)

    if not reference:
        return None

    # Exact admission number first.
    student = (
        Student.objects
        .filter(
            admission_no__iexact=reference,
            is_active=True,
        )
        .first()
    )

    if student:
        return student

    # Allow common prefixes configured by the school.
    config = get_config()

    prefix = (
        str(
            getattr(
                config,
                "mpesa_paybill_account",
                "",
            )
            or ""
        )
        .strip()
        .upper()
    )

    if prefix and reference.startswith(prefix):
        remainder = reference[len(prefix):].strip(" -_/")

        student = (
            Student.objects
            .filter(
                admission_no__iexact=remainder,
                is_active=True,
            )
            .first()
        )

        if student:
            return student

    return None


def get_current_fee_record(student):
    return (
        student.fee_records
        .select_related("academic_year", "term")
        .order_by(
            "-academic_year__year",
            "-term__id",
            "-id",
        )
        .first()
    )


def _decimal(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def validate_c2b_payload(payload):
    config = get_config()

    if not config:
        return False, "Automatic payment settings are not configured."

    if not config.is_active:
        return False, "Automatic payments are disabled."

    if not config.mpesa_paybill_enabled:
        return False, "M-Pesa PayBill payments are disabled."

    expected_shortcode = configured_shortcode()

    received_shortcode = str(
        payload.get("BusinessShortCode")
        or payload.get("BusinessShortCode")
        or ""
    ).strip()

    if (
        expected_shortcode
        and received_shortcode
        and received_shortcode != expected_shortcode
    ):
        return False, "Payment was sent to an unexpected PayBill shortcode."

    transaction_id = str(
        payload.get("TransID")
        or ""
    ).strip()

    if not transaction_id:
        return False, "Missing M-Pesa transaction ID."

    try:
        amount = Decimal(
            str(
                payload.get("TransAmount")
                or payload.get("Amount")
                or "0"
            )
        )
    except (InvalidOperation, ValueError, TypeError):
        return False, "Invalid transaction amount."

    if amount <= 0:
        return False, "Transaction amount must be greater than zero."

    reference = str(
        payload.get("BillRefNumber")
        or payload.get("AccountReference")
        or ""
    ).strip()

    if not reference:
        return False, "Learner admission/reference number is missing."

    student = find_student_from_reference(reference)

    if not student:
        return False, (
            "Learner could not be found from the PayBill "
            "account/reference number."
        )

    fee_record = get_current_fee_record(student)

    if not fee_record:
        return False, "No fee record was found for this learner."

    balance = _decimal(
        getattr(fee_record, "balance", 0)
    )

    if balance <= 0:
        return False, "The learner has no outstanding fee balance."

    if amount > balance:
        return False, (
            "Payment exceeds the learner's current fee balance."
        )

    existing = (
        MpesaPaybillTransaction.objects
        .filter(transaction_id__iexact=transaction_id)
        .first()
    )

    if existing:
        return False, "This M-Pesa transaction has already been received."

    return True, "Accepted"


def save_confirmation(payload):
    transaction_id = str(
        payload.get("TransID")
        or ""
    ).strip()

    if not transaction_id:
        raise ValueError(
            "M-Pesa confirmation did not contain TransID."
        )

    # IMPORTANT:
    # Validate BEFORE creating the MpesaPaybillTransaction record.
    # Otherwise validate_c2b_payload() sees the newly-created record
    # and incorrectly reports the transaction as already received.
    ok, message = validate_c2b_payload(payload)

    if not ok:
        # If the transaction already exists, return the existing record.
        existing = (
            MpesaPaybillTransaction.objects
            .filter(transaction_id__iexact=transaction_id)
            .first()
        )

        if existing:
            return existing, False

        # Store rejected transactions for audit purposes.
        amount = _decimal(
            payload.get("TransAmount")
            or payload.get("Amount")
        )

        reference = str(
            payload.get("BillRefNumber")
            or payload.get("AccountReference")
            or ""
        ).strip()

        student = find_student_from_reference(reference)

        fee_record = (
            get_current_fee_record(student)
            if student
            else None
        )

        c2b = MpesaPaybillTransaction.objects.create(
            transaction_id=transaction_id,
            transaction_time=str(
                payload.get("TransTime") or ""
            ),
            transaction_amount=amount,
            business_short_code=str(
                payload.get("BusinessShortCode")
                or ""
            ),
            bill_ref_number=reference,
            invoice_number=str(
                payload.get("InvoiceNumber")
                or ""
            ),
            org_account_balance=str(
                payload.get("OrgAccountBalance")
                or ""
            ),
            third_party_trans_id=str(
                payload.get("ThirdPartyTransID")
                or ""
            ),
            msisdn=str(
                payload.get("MSISDN")
                or ""
            ),
            first_name=str(
                payload.get("FirstName")
                or ""
            ),
            middle_name=str(
                payload.get("MiddleName")
                or ""
            ),
            last_name=str(
                payload.get("LastName")
                or ""
            ),
            student=student,
            fee_record=fee_record,
            status="REJECTED",
            raw_payload=payload,
            verification_message=message,
        )

        return c2b, True

    with transaction.atomic():

        # Race-condition protection.
        existing = (
            MpesaPaybillTransaction.objects
            .select_for_update()
            .filter(transaction_id__iexact=transaction_id)
            .first()
        )

        if existing:
            return existing, False

        amount = _decimal(
            payload.get("TransAmount")
            or payload.get("Amount")
        )

        reference = str(
            payload.get("BillRefNumber")
            or payload.get("AccountReference")
            or ""
        ).strip()

        student = find_student_from_reference(reference)

        if not student:
            raise ValueError(
                "Learner could not be found from the PayBill reference."
            )

        fee_record = get_current_fee_record(student)

        if not fee_record:
            raise ValueError(
                "No fee record was found for this learner."
            )

        c2b = MpesaPaybillTransaction.objects.create(
            transaction_id=transaction_id,
            transaction_time=str(
                payload.get("TransTime") or ""
            ),
            transaction_amount=amount,
            business_short_code=str(
                payload.get("BusinessShortCode")
                or ""
            ),
            bill_ref_number=reference,
            invoice_number=str(
                payload.get("InvoiceNumber")
                or ""
            ),
            org_account_balance=str(
                payload.get("OrgAccountBalance")
                or ""
            ),
            third_party_trans_id=str(
                payload.get("ThirdPartyTransID")
                or ""
            ),
            msisdn=str(
                payload.get("MSISDN")
                or ""
            ),
            first_name=str(
                payload.get("FirstName")
                or ""
            ),
            middle_name=str(
                payload.get("MiddleName")
                or ""
            ),
            last_name=str(
                payload.get("LastName")
                or ""
            ),
            student=student,
            fee_record=fee_record,
            status="VALIDATED",
            raw_payload=payload,
            validation_response={
                "ResultCode": 0,
                "ResultDesc": "Accepted",
            },
            verification_message=(
                "C2B payment accepted for reconciliation."
            ),
        )

        # Final balance check immediately before posting.
        balance = _decimal(
            getattr(fee_record, "balance", 0)
        )

        if amount > balance:
            c2b.status = "REJECTED"
            c2b.verification_message = (
                "Payment exceeds the current fee balance."
            )
            c2b.save(
                update_fields=[
                    "status",
                    "verification_message",
                    "updated_at",
                ]
            )
            return c2b, True

        # Additional duplicate protection against FeePayment.
        duplicate = (
            FeePayment.objects
            .filter(reference=c2b.transaction_id)
            .first()
        )

        if duplicate:
            c2b.fee_payment = duplicate
            c2b.status = "DUPLICATE"
            c2b.verification_message = (
                "An official fee payment already exists for this transaction."
            )
            c2b.verified_at = timezone.now()
            c2b.save(
                update_fields=[
                    "fee_payment",
                    "status",
                    "verification_message",
                    "verified_at",
                    "updated_at",
                ]
            )
            return c2b, True

        # Create the official school FeePayment.
        payment = FeePayment.objects.create(
            fee_record=fee_record,
            amount=amount,
            payment_date=timezone.now().date(),
            payment_method="M-Pesa PayBill",
            reference=c2b.transaction_id,
        )

        c2b.fee_payment = payment
        c2b.status = "VERIFIED"
        c2b.verification_message = (
            "M-Pesa PayBill payment automatically verified "
            "and posted to the learner's fee account."
        )
        c2b.verified_at = timezone.now()

        c2b.save(
            update_fields=[
                "fee_payment",
                "status",
                "verification_message",
                "verified_at",
                "updated_at",
            ]
        )

        return c2b, True

