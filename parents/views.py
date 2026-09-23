from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden

from .models import Parent
from students.models import Student
from fees.models import FeeRecord


@login_required
def parent_dashboard(request):

    parent = Parent.objects.filter(
        user=request.user
    ).first()

    children = parent.children.all() if parent else []

    return render(
        request,
        "parents/parent_dashboard.html",
        {
            "parent": parent,
            "children": children,
        }
    )


@login_required
def child_portal(request, student_id):

    parent = Parent.objects.filter(
        user=request.user
    ).first()

    if not parent:
        return HttpResponseForbidden(
            "Parent account not found."
        )

    child = get_object_or_404(
        Student,
        id=student_id
    )

    # Security:
    # Parent can only access their own child.
    if not parent.children.filter(
        id=child.id
    ).exists():

        return HttpResponseForbidden(
            "You are not authorised to access this learner."
        )

    return render(
        request,
        "parents/child_portal.html",
        {
            "parent": parent,
            "child": child,
        }
    )


@login_required
def child_fees(request, student_id):

    parent = Parent.objects.filter(
        user=request.user
    ).first()

    if not parent:
        return HttpResponseForbidden(
            "Parent account not found."
        )

    child = get_object_or_404(
        Student,
        id=student_id
    )

    # Security:
    # Parent can only see fees belonging to their own child.
    if not parent.children.filter(
        id=child.id
    ).exists():

        return HttpResponseForbidden(
            "You are not authorised to access this learner."
        )

    # --------------------------------------------------
    # GET ALL FEE RECORDS FOR THIS LEARNER
    # --------------------------------------------------

    fee_records = list(
        FeeRecord.objects
        .filter(student=child)
        .select_related(
            "academic_year",
            "term"
        )
        .prefetch_related("payments")
        .order_by(
            "-academic_year__year",
            "-term__order",
            "-id"
        )
    )

    # --------------------------------------------------
    # TOTALS
    # --------------------------------------------------

    total_opening_balance = sum(
        record.opening_balance
        for record in fee_records
    )

    total_amount_charged = sum(
        record.amount_charged
        for record in fee_records
    )

    total_amount_paid = sum(
        record.amount_paid
        for record in fee_records
    )

    total_balance = (
        total_opening_balance
        + total_amount_charged
        - total_amount_paid
    )

    # --------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------

    payments = []

    for record in fee_records:

        for payment in record.payments.all():

            payments.append({
                "record": record,
                "payment": payment,
            })

    return render(
        request,
        "parents/child_fees.html",
        {
            "parent": parent,
            "child": child,

            "fee_records": fee_records,
            "payments": payments,

            "total_opening_balance":
                total_opening_balance,

            "total_amount_charged":
                total_amount_charged,

            "total_amount_paid":
                total_amount_paid,

            "total_balance":
                total_balance,
        }
    )