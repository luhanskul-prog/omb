from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from students.models import Student
from .models import FeeRecord, OnlinePayment
from .payment_method_access import require_automatic_payment
from .alternate_payment_auto import _payer_role, _authorized_student
from .services.automatic_mpesa import (
    initiate_automatic_stk_push,
    AutomaticMpesaError,
)


@login_required
def paybill_payment_page(request):
    admission_no = (
        request.GET.get("admission_no")
        or request.POST.get("admission_no")
        or ""
    ).strip()

    payer_role = _payer_role(request)

    if payer_role not in {"ADMIN", "PARENT", "STUDENT"}:
        messages.error(
            request,
            "Your account is not authorized to make PayBill payments.",
        )
        return redirect("accounts:login")

    try:
        config = require_automatic_payment("MPESA_PAYBILL")
    except RuntimeError as exc:
        return render(
            request,
            "fees/paybill_payment.html",
            {
                "disabled": True,
                "error": str(exc),
                "admission_no": admission_no,
            },
            status=403,
        )

    student = _authorized_student(
        request,
        admission_no,
    )

    if not student:
        return render(
            request,
            "fees/paybill_payment.html",
            {
                "disabled": True,
                "error": "Student was not found.",
                "admission_no": admission_no,
            },
            status=404,
        )

    fee_record = (
        FeeRecord.objects
        .filter(student=student)
        .order_by("-id")
        .first()
    )

    if not fee_record:
        return render(
            request,
            "fees/paybill_payment.html",
            {
                "disabled": True,
                "error": "No fee record was found for this student.",
                "student": student,
            },
            status=404,
        )

    balance = fee_record.balance

    if request.method == "POST":

        amount_raw = (
            request.POST.get("amount")
            or request.POST.get("payment_amount")
            or ""
        ).strip()

        phone_number = (
            request.POST.get("phone_number")
            or request.POST.get("phone")
            or request.POST.get("mpesa_phone")
            or ""
        ).strip()

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            amount = Decimal("0")

        if amount <= 0:
            return render(
                request,
                "fees/paybill_payment.html",
                {
                    "student": student,
                    "fee_record": fee_record,
                    "balance": balance,
                    "config": config,
                    "admission_no": admission_no,
                    "error": "Enter a valid payment amount.",
                },
                status=400,
            )

        if amount > balance:
            return render(
                request,
                "fees/paybill_payment.html",
                {
                    "student": student,
                    "fee_record": fee_record,
                    "balance": balance,
                    "config": config,
                    "admission_no": admission_no,
                    "error": (
                        f"Payment cannot exceed the outstanding "
                        f"balance of KSh {balance:,.2f}."
                    ),
                },
                status=400,
            )

        if not phone_number:
            return render(
                request,
                "fees/paybill_payment.html",
                {
                    "student": student,
                    "fee_record": fee_record,
                    "balance": balance,
                    "config": config,
                    "admission_no": admission_no,
                    "error": "Enter the M-Pesa phone number.",
                },
                status=400,
            )

        # ----------------------------------------------------
        # FIND THE USER WHO OWNS THIS PAYMENT
        # ----------------------------------------------------

        payer = request.user

        # ----------------------------------------------------
        # CREATE PAYMENT USING THE ACTUAL OnlinePayment MODEL
        # ----------------------------------------------------

        payment = OnlinePayment.objects.create(
            fee_record=fee_record,
            payer=payer,
            payer_role=payer_role,
            amount=amount,
            payment_method="MPESA_PAYBILL",
            status="PENDING",
            phone_number=phone_number,
            account_reference=(
                getattr(student, "admission_no", None)
                or f"PAYBILL-{fee_record.id}"
            ),
        )

        reference = (
            payment.account_reference
            or f"PAYBILL-{payment.id}"
        )

        # ----------------------------------------------------
        # SEND STK USING PAYBILL-SPECIFIC CONFIGURATION
        # ----------------------------------------------------

        try:
            result = initiate_automatic_stk_push(
                phone_number=phone_number,
                amount=amount,
                method="MPESA_PAYBILL",
                account_reference=reference,
                transaction_desc="School Fees",
            )

        except AutomaticMpesaError as exc:

            payment.status = "FAILED"
            payment.verification_message = str(exc)
            payment.save(
                update_fields=[
                    "status",
                    "verification_message",
                    "updated_at",
                ]
            )

            return render(
                request,
                "fees/paybill_payment.html",
                {
                    "student": student,
                    "fee_record": fee_record,
                    "balance": balance,
                    "config": config,
                    "admission_no": admission_no,
                    "error": str(exc),
                },
                status=400,
            )

        # ----------------------------------------------------
        # SAVE DARAJA RESPONSE
        # ----------------------------------------------------

        payment.merchant_request_id = (
            result.get("MerchantRequestID") or ""
        )

        payment.checkout_request_id = (
            result.get("CheckoutRequestID") or ""
        )

        payment.provider_response_code = (
            result.get("ResponseCode") or ""
        )

        payment.provider_response_description = (
            result.get("ResponseDescription")
            or ""
        )

        payment.provider_raw_response = result

        payment.verification_message = (
            result.get("CustomerMessage")
            or result.get("ResponseDescription")
            or "STK request sent successfully."
        )

        payment.save()

        # ----------------------------------------------------
        # GO TO EXISTING PAYMENT STATUS PAGE
        # ----------------------------------------------------

        return redirect(
            "fees:online_payment_status",
            payment_id=payment.id,
        )

    return render(
        request,
        "fees/paybill_payment.html",
        {
            "student": student,
            "fee_record": fee_record,
            "balance": balance,
            "config": config,
            "admission_no": admission_no,
            "paybill_number": config.mpesa_paybill_number,
            "paybill_account": config.mpesa_paybill_account,
        },
    )
