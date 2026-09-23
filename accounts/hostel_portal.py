from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from hostel.models import (
    Hostel,
    Room,
    StudentHostelAllocation,
    HostelIncident,
    HostelApplication,
)

from students.models import Student


# ============================================================
# HELPERS
# ============================================================

def _portal_student(request):
    """
    Return the Student linked to the logged-in student account.
    """
    profile = getattr(request.user, "profile", None)

    student = getattr(profile, "student", None)

    if student:
        return student

    student = getattr(request.user, "student", None)

    if student:
        return student

    return None


def _parent_children(request):
    parent = getattr(request.user, "parent", None)

    if not parent:
        return Student.objects.none()

    return parent.children.all().order_by(
        "admission_no",
        "first_name",
    )


def _parent_child(request, student_id):
    return get_object_or_404(
        _parent_children(request),
        pk=student_id,
    )


# ============================================================
# STUDENT HOSTEL
# ============================================================

@login_required
def student_hostel(request):

    student = _portal_student(request)

    if not student:
        messages.error(
            request,
            "Your account is not linked to a student record.",
        )
        return redirect("accounts:login")

    applications = (
        HostelApplication.objects
        .filter(student=student)
        .select_related("hostel", "room")
        .order_by("-created_at")
    )

    allocations = (
        StudentHostelAllocation.objects
        .filter(student=student)
        .select_related("hostel", "room", "bed")
        .order_by("-admission_date")
    )

    incidents = (
        HostelIncident.objects
        .filter(student=student)
        .select_related("hostel")
        .order_by("-incident_date", "-id")[:10]
    )

    return render(
        request,
        "accounts/student_hostel.html",
        {
            "student": student,
            "applications": applications,
            "allocations": allocations,
            "incidents": incidents,
            "hostels": Hostel.objects.filter(
                is_active=True
            ).order_by("name"),
        },
    )


@login_required
def student_hostel_apply(request):

    student = _portal_student(request)

    if not student:
        messages.error(
            request,
            "Your account is not linked to a student record.",
        )
        return redirect("accounts:login")

    if request.method == "POST":

        hostel_id = request.POST.get("hostel")
        room_id = request.POST.get("room")
        requested_date = request.POST.get("requested_date")
        reason = request.POST.get("reason", "").strip()

        hostel = get_object_or_404(
            Hostel,
            pk=hostel_id,
            is_active=True,
        )

        room = None

        if room_id:
            room = get_object_or_404(
                Room,
                pk=room_id,
                hostel=hostel,
                is_active=True,
            )

        if not requested_date:
            messages.error(
                request,
                "Please select your requested admission date.",
            )
            return redirect(
                "accounts:student_hostel_apply"
            )

        existing = HostelApplication.objects.filter(
            student=student,
            status="pending",
        ).exists()

        if existing:
            messages.warning(
                request,
                "You already have a pending hostel application.",
            )
            return redirect(
                "accounts:student_hostel"
            )

        HostelApplication.objects.create(
            student=student,
            hostel=hostel,
            room=room,
            requested_date=requested_date,
            reason=reason,
        )

        messages.success(
            request,
            "Your hostel application has been submitted successfully.",
        )

        return redirect(
            "accounts:student_hostel"
        )

    return render(
        request,
        "accounts/student_hostel_apply.html",
        {
            "student": student,
            "hostels": Hostel.objects.filter(
                is_active=True
            ).order_by("name"),
        },
    )


@login_required
def student_hostel_incident(request):

    student = _portal_student(request)

    if not student:
        messages.error(
            request,
            "Your account is not linked to a student record.",
        )
        return redirect("accounts:login")

    allocation = (
        StudentHostelAllocation.objects
        .filter(
            student=student,
            status="active",
        )
        .select_related("hostel")
        .first()
    )

    if request.method == "POST":

        hostel_id = request.POST.get("hostel")

        hostel = get_object_or_404(
            Hostel,
            pk=hostel_id,
            is_active=True,
        )

        title = request.POST.get(
            "title",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        severity = request.POST.get(
            "severity",
            "low",
        )

        if not title or not description:
            messages.error(
                request,
                "Please provide an incident title and description.",
            )
            return redirect(
                "accounts:student_hostel_incident"
            )

        HostelIncident.objects.create(
            student=student,
            hostel=hostel,
            title=title,
            description=description,
            severity=severity,
            incident_date=timezone.localdate(),
        )

        messages.success(
            request,
            "Your hostel incident report has been submitted.",
        )

        return redirect(
            "accounts:student_hostel"
        )

    hostels = Hostel.objects.filter(
        is_active=True
    ).order_by("name")

    return render(
        request,
        "accounts/student_hostel_incident.html",
        {
            "student": student,
            "allocation": allocation,
            "hostels": hostels,
        },
    )


# ============================================================
# PARENT HOSTEL
# ============================================================

@login_required
def parent_hostel(request):

    children = list(
        _parent_children(request)
    )

    child_data = []

    for child in children:

        allocations = (
            StudentHostelAllocation.objects
            .filter(student=child)
            .select_related(
                "hostel",
                "room",
                "bed",
            )
            .order_by("-admission_date")
        )

        applications = (
            HostelApplication.objects
            .filter(student=child)
            .select_related(
                "hostel",
                "room",
            )
            .order_by("-created_at")
        )

        incidents = (
            HostelIncident.objects
            .filter(student=child)
            .select_related("hostel")
            .order_by(
                "-incident_date",
                "-id",
            )[:5]
        )

        child_data.append(
            {
                "student": child,
                "allocations": allocations,
                "applications": applications,
                "incidents": incidents,
            }
        )

    return render(
        request,
        "accounts/parent_hostel.html",
        {
            "children": children,
            "child_data": child_data,
            "hostels": Hostel.objects.filter(
                is_active=True
            ).order_by("name"),
        },
    )


@login_required
def parent_hostel_apply(request, student_id):

    child = _parent_child(
        request,
        student_id,
    )

    if request.method == "POST":

        hostel_id = request.POST.get("hostel")
        room_id = request.POST.get("room")
        requested_date = request.POST.get("requested_date")
        reason = request.POST.get("reason", "").strip()

        hostel = get_object_or_404(
            Hostel,
            pk=hostel_id,
            is_active=True,
        )

        room = None

        if room_id:
            room = get_object_or_404(
                Room,
                pk=room_id,
                hostel=hostel,
                is_active=True,
            )

        if not requested_date:
            messages.error(
                request,
                "Please select the requested admission date.",
            )
            return redirect(
                "accounts:parent_hostel_apply",
                student_id=student_id,
            )

        pending = HostelApplication.objects.filter(
            student=child,
            status="pending",
        ).exists()

        if pending:
            messages.warning(
                request,
                f"{child.first_name} already has a pending hostel application.",
            )
            return redirect(
                "accounts:parent_hostel"
            )

        HostelApplication.objects.create(
            student=child,
            hostel=hostel,
            room=room,
            requested_date=requested_date,
            reason=reason,
        )

        messages.success(
            request,
            f"Hostel application submitted for {child.first_name}.",
        )

        return redirect(
            "accounts:parent_hostel"
        )

    return render(
        request,
        "accounts/parent_hostel_apply.html",
        {
            "child": child,
            "hostels": Hostel.objects.filter(
                is_active=True
            ).order_by("name"),
        },
    )


@login_required
def parent_hostel_incident(request, student_id):

    child = _parent_child(
        request,
        student_id,
    )

    allocation = (
        StudentHostelAllocation.objects
        .filter(
            student=child,
            status="active",
        )
        .select_related("hostel")
        .first()
    )

    if request.method == "POST":

        hostel_id = request.POST.get("hostel")

        hostel = get_object_or_404(
            Hostel,
            pk=hostel_id,
            is_active=True,
        )

        title = request.POST.get(
            "title",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        severity = request.POST.get(
            "severity",
            "low",
        )

        if not title or not description:
            messages.error(
                request,
                "Please provide an incident title and description.",
            )
            return redirect(
                "accounts:parent_hostel_incident",
                student_id=student_id,
            )

        HostelIncident.objects.create(
            student=child,
            hostel=hostel,
            title=title,
            description=description,
            severity=severity,
            incident_date=timezone.localdate(),
        )

        messages.success(
            request,
            f"Incident report submitted for {child.first_name}.",
        )

        return redirect(
            "accounts:parent_hostel"
        )

    return render(
        request,
        "accounts/parent_hostel_incident.html",
        {
            "child": child,
            "allocation": allocation,
            "hostels": Hostel.objects.filter(
                is_active=True
            ).order_by("name"),
        },
    )
