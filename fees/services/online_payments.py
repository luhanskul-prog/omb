
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from fees.models import (
    FeePayment,
    FeeRecord,
    OnlinePayment,
    PaymentMethod,
)


class OnlinePaymentError(Exception):
    """Expected online-payment validation error."""


def get_student_fee_record(student, fee_record_id):
    """
    Safely obtain a fee record belonging to the selected student.
    """

    try:
        return FeeRecord.objects.select_related(
            "student",
            "academic_year",
            "term",
        ).get(
            id=fee_record_id,
            student=student,
        )
    except FeeRecord.DoesNotExist:
        raise OnlinePaymentError(
            "The selected fee record does not exist for this student."
        )


def validate_payment_amount(fee_record, amount):
    """
    Validate that the requested amount is positive and does not
    exceed the current outstanding balance.
    """

    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise OnlinePaymentError(
            "Enter a valid payment amount."
        )

    amount = amount.quantize(Decimal("0.01"))

    if amount <= Decimal("0.00"):
        raise OnlinePaymentError(
            "Payment amount must be greater than zero."
        )

    # Always obtain the current balance from the database object.
    balance = Decimal(str(fee_record.balance))

    if balance <= Decimal("0.00"):
        raise OnlinePaymentError(
            "This fee record has no outstanding balance."
        )

    if amount > balance:
        raise OnlinePaymentError(
            f"Payment cannot exceed the outstanding balance of "
            f"KSh {balance:,.2f}."
        )

    return amount


def validate_fee_record(fee_record):
    """
    Validate whether this fee record can receive an online payment.
    """

    if not fee_record:
        raise OnlinePaymentError(
            "Fee record was not found."
        )

    term = fee_record.term

    if term.is_closed:
        raise OnlinePaymentError(
            "This term is closed. Online payment is not allowed."
        )

    if not term.is_active:
        raise OnlinePaymentError(
            "This term is not currently active."
        )

    return True


def validate_payment_method(method_code, payer_role):
    """
    Confirm that the requested payment method is enabled and
    available to the current payer role.
    """

    try:
        method = PaymentMethod.objects.get(
            code=method_code,
            is_enabled=True,
            online_enabled=True,
        )
    except PaymentMethod.DoesNotExist:
        raise OnlinePaymentError(
            "The selected payment method is unavailable."
        )

    if payer_role == "PARENT" and not method.available_to_parents:
        raise OnlinePaymentError(
            "This payment method is not available to parents."
        )

    if payer_role == "STUDENT" and not method.available_to_students:
        raise OnlinePaymentError(
            "This payment method is not available to students."
        )

    if payer_role == "ADMIN" and not method.available_to_admin:
        raise OnlinePaymentError(
            "This payment method is not available to administrators."
        )

    return method


def get_available_payment_methods(payer_role):
    """
    Return enabled online payment methods available to the payer.
    """

    methods = PaymentMethod.objects.filter(
        is_enabled=True,
        online_enabled=True,
    )

    if payer_role == "PARENT":
        methods = methods.filter(available_to_parents=True)

    elif payer_role == "STUDENT":
        methods = methods.filter(available_to_students=True)

    elif payer_role == "ADMIN":
        methods = methods.filter(available_to_admin=True)

    else:
        methods = methods.none()

    return methods.order_by("sort_order", "name")


def create_online_payment(
    *,
    payer,
    payer_role,
    student,
    fee_record_id,
    amount,
    payment_method_code,
    phone_number="",
):
    """
    Create an INITIATED online payment.

    This function does NOT create FeePayment.

    FeePayment is created only after the provider confirms
    successful payment.
    """

    if not isinstance(payer, User):
        raise OnlinePaymentError(
            "Invalid payer account."
        )

    if payer_role not in {"ADMIN", "PARENT", "STUDENT"}:
        raise OnlinePaymentError(
            "Invalid payer role."
        )

    fee_record = get_student_fee_record(
        student,
        fee_record_id,
    )

    validate_fee_record(fee_record)

    amount = validate_payment_amount(
        fee_record,
        amount,
    )

    method = validate_payment_method(
        payment_method_code,
        payer_role,
    )

    phone_number = (phone_number or "").strip()

    if method.method_type == "MPESA" and not phone_number:
        raise OnlinePaymentError(
            "A phone number is required for M-Pesa payment."
        )

    with transaction.atomic():

        # Lock the fee record so two simultaneous payment requests
        # cannot both rely on the same old balance.
        locked_record = FeeRecord.objects.select_for_update().select_related(
            "student",
            "academic_year",
            "term",
        ).get(
            id=fee_record.id
        )

        validate_fee_record(locked_record)

        amount = validate_payment_amount(
            locked_record,
            amount,
        )

        online_payment = OnlinePayment.objects.create(
            fee_record=locked_record,
            payer=payer,
            payer_role=payer_role,
            amount=amount,
            payment_method=method.method_type,
            status="INITIATED",
            phone_number=phone_number,
            account_reference=(
                method.mpesa_account_reference
                or locked_record.student.admission_no
            ),
        )

    return online_payment


@transaction.atomic
def mark_payment_verified(
    online_payment,
    *,
    provider_receipt="",
    transaction_reference="",
    provider_response_code="",
    provider_response_description="",
    provider_raw_response=None,
):
    """
    Convert a successfully verified online transaction into the
    official FeePayment.

    This operation is idempotent:
    if the online transaction has already been verified, the
    existing FeePayment is returned instead of creating another.
    """

    locked_payment = OnlinePayment.objects.select_for_update().select_related(
        "fee_record",
        "fee_record__student",
        "fee_record__term",
    ).get(
        id=online_payment.id
    )

    # Already processed successfully.
    if (
        locked_payment.status == "VERIFIED"
        and locked_payment.fee_payment_id
    ):
        return locked_payment.fee_payment

    fee_record = FeeRecord.objects.select_for_update().get(
        id=locked_payment.fee_record_id
    )

    if fee_record.term.is_closed:
        locked_payment.status = "FAILED"
        locked_payment.verification_message = (
            "Payment could not be posted because the term is closed."
        )
        locked_payment.save(
            update_fields=[
                "status",
                "verification_message",
                "updated_at",
            ]
        )

        raise OnlinePaymentError(
            "The fee term is closed."
        )

    amount = Decimal(str(locked_payment.amount))
    current_balance = Decimal(str(fee_record.balance))

    if amount <= Decimal("0.00"):
        raise OnlinePaymentError(
            "Invalid payment amount."
        )

    if amount > current_balance:
        locked_payment.status = "FAILED"
        locked_payment.verification_message = (
            "Verified provider amount exceeds the current fee balance."
        )
        locked_payment.save(
            update_fields=[
                "status",
                "verification_message",
                "updated_at",
            ]
        )

        raise OnlinePaymentError(
            "Verified payment exceeds the current fee balance."
        )

    # Protect against the same provider receipt being posted twice.
    if provider_receipt:
        duplicate = FeePayment.objects.filter(
            reference=provider_receipt
        ).exclude(
            online_transaction=locked_payment
        ).first()

        if duplicate:
            locked_payment.status = "VERIFIED"
            locked_payment.fee_payment = duplicate
            locked_payment.provider_receipt = provider_receipt
            locked_payment.transaction_reference = transaction_reference
            locked_payment.verified_at = timezone.now()
            locked_payment.verification_message = (
                "Provider transaction was already posted."
            )
            locked_payment.save()

            return duplicate

    fee_payment = FeePayment.objects.create(
        fee_record=fee_record,
        amount=amount,
        payment_date=timezone.localdate(),
        payment_method="Online " + locked_payment.payment_method,
        reference=provider_receipt or transaction_reference,
    )

    locked_payment.status = "VERIFIED"
    locked_payment.provider_receipt = provider_receipt
    locked_payment.transaction_reference = transaction_reference
    locked_payment.provider_response_code = provider_response_code
    locked_payment.provider_response_description = (
        provider_response_description
    )
    locked_payment.provider_raw_response = provider_raw_response
    locked_payment.verified_at = timezone.now()
    locked_payment.verification_message = (
        "Payment verified and official fee payment created."
    )
    locked_payment.fee_payment = fee_payment

    locked_payment.save()

    return fee_payment


def mark_payment_failed(
    online_payment,
    *,
    response_code="",
    response_description="",
    raw_response=None,
    status="FAILED",
):
    """
    Safely mark an online payment as failed/cancelled/expired.
    """

    allowed_statuses = {
        "FAILED",
        "CANCELLED",
        "EXPIRED",
        "REVERSED",
    }

    if status not in allowed_statuses:
        status = "FAILED"

    online_payment.status = status
    online_payment.provider_response_code = response_code
    online_payment.provider_response_description = (
        response_description
    )
    online_payment.provider_raw_response = raw_response
    online_payment.verification_message = response_description

    online_payment.save(
        update_fields=[
            "status",
            "provider_response_code",
            "provider_response_description",
            "provider_raw_response",
            "verification_message",
            "updated_at",
        ]
    )

    return online_payment


def get_payment_status(online_payment_id, payer=None):
    """
    Return an online transaction while optionally restricting it
    to the initiating payer.
    """

    queryset = OnlinePayment.objects.select_related(
        "fee_record",
        "fee_record__student",
        "fee_payment",
    )

    if payer is not None:
        queryset = queryset.filter(payer=payer)

    try:
        return queryset.get(id=online_payment_id)
    except OnlinePayment.DoesNotExist:
        raise OnlinePaymentError(
            "Online payment was not found."
        )
