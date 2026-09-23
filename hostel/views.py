from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render

from accounts.staff_access import role_permission_required

from .models import (
    Hostel,
    Room,
    Bed,
    StudentHostelAllocation,
    HostelAttendance,
    HostelFee,
    HostelIncident,
)

from .forms import (
    HostelForm,
    RoomForm,
    BedForm,
    AllocationForm,
    HostelFeeForm,
    HostelIncidentForm,
)


def branding_context():

    try:
        from accounts.models import SchoolBranding

        return {
            "branding": SchoolBranding.objects.filter(
                is_active=True
            ).first()
        }

    except Exception:
        return {
            "branding": None
        }


@login_required
@role_permission_required("view_hostel", "hostel")
def hostel_dashboard(request):

    total_hostels = Hostel.objects.filter(is_active=True).count()
    total_rooms = Room.objects.filter(is_active=True).count()
    total_beds = Bed.objects.count()

    occupied_beds = Bed.objects.filter(
        status="occupied"
    ).count()

    available_beds = Bed.objects.filter(
        status="available"
    ).count()

    reserved_beds = Bed.objects.filter(
        status="reserved"
    ).count()

    maintenance_beds = Bed.objects.filter(
        status="maintenance"
    ).count()

    active_boarders = StudentHostelAllocation.objects.filter(
        status="active"
    ).count()

    outstanding_fees = HostelFee.objects.filter(
        paid=False
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    today = date.today()

    today_attendance = HostelAttendance.objects.filter(
        date=today
    )

    present_today = today_attendance.filter(
        status="present"
    ).count()

    absent_today = today_attendance.filter(
        status="absent"
    ).count()

    late_today = today_attendance.filter(
        status="late"
    ).count()

    permission_today = today_attendance.filter(
        status="permission"
    ).count()

    incidents_open = HostelIncident.objects.filter(
        resolved=False
    ).count()

    hostels = Hostel.objects.annotate(
        room_count=Count("rooms", distinct=True),
        allocation_count=Count(
            "student_allocations",
            filter=Q(
                student_allocations__status="active"
            ),
            distinct=True,
        ),
    ).order_by("name")[:8]

    recent_allocations = (
        StudentHostelAllocation.objects
        .select_related(
            "student",
            "hostel",
            "room",
            "bed",
        )
        .order_by("-id")[:8]
    )

    recent_incidents = (
        HostelIncident.objects
        .select_related("student", "hostel")
        .order_by("-incident_date", "-id")[:6]
    )

    recent_fees = (
        HostelFee.objects
        .select_related("student", "hostel")
        .order_by("-due_date", "-id")[:6]
    )

    context = {
        **branding_context(),

        "total_hostels": total_hostels,
        "total_rooms": total_rooms,
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "reserved_beds": reserved_beds,
        "maintenance_beds": maintenance_beds,
        "active_boarders": active_boarders,

        "outstanding_fees": outstanding_fees,

        "present_today": present_today,
        "absent_today": absent_today,
        "late_today": late_today,
        "permission_today": permission_today,

        "incidents_open": incidents_open,

        "hostels": hostels,
        "recent_allocations": recent_allocations,
        "recent_incidents": recent_incidents,
        "recent_fees": recent_fees,
    }

    return render(
        request,
        "hostel/dashboard.html",
        context,
    )


# ============================================================
# HOSTELS
# ============================================================

@login_required
@role_permission_required("view_hostel", "hostel")
def hostels(request):

    search = request.GET.get("search", "").strip()

    qs = Hostel.objects.all()

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(location__icontains=search)
            | Q(warden_name__icontains=search)
        )

    hostels = qs.annotate(
        room_count=Count(
            "rooms",
            distinct=True
        ),
        bed_count=Count(
            "rooms__beds",
            distinct=True
        ),
        occupied_count=Count(
            "rooms__beds",
            filter=Q(
                rooms__beds__status="occupied"
            ),
            distinct=True,
        ),
    )

    return render(
        request,
        "hostel/hostels.html",
        {
            **branding_context(),
            "hostels": hostels,
            "search": search,
        },
    )


@login_required
@role_permission_required("add_hostel", "hostel")
def hostel_create(request):

    form = HostelForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel created successfully."
        )

        return redirect("hostel:hostels")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Add Hostel",
            "subtitle": "Create a boarding facility",
            "back_url": "hostel:hostels",
        },
    )


@login_required
@role_permission_required("change_hostel", "hostel")
def hostel_edit(request, pk):

    hostel = get_object_or_404(
        Hostel,
        pk=pk
    )

    form = HostelForm(
        request.POST or None,
        instance=hostel
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel updated successfully."
        )

        return redirect("hostel:hostels")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Hostel",
            "subtitle": hostel.name,
            "back_url": "hostel:hostels",
        },
    )


# ============================================================
# ROOMS
# ============================================================

@login_required
@role_permission_required("view_room", "hostel")
def rooms(request):

    search = request.GET.get("search", "").strip()
    hostel_id = request.GET.get("hostel", "").strip()

    qs = Room.objects.select_related(
        "hostel"
    ).prefetch_related("beds")

    if search:
        qs = qs.filter(
            Q(room_number__icontains=search)
            | Q(hostel__name__icontains=search)
        )

    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    return render(
        request,
        "hostel/rooms.html",
        {
            **branding_context(),
            "rooms": qs,
            "hostels": Hostel.objects.filter(
                is_active=True
            ),
            "search": search,
            "hostel_id": hostel_id,
        },
    )


@login_required
@role_permission_required("add_room", "hostel")
def room_create(request):

    form = RoomForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Room created successfully."
        )

        return redirect("hostel:rooms")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Add Room",
            "subtitle": "Create a hostel room",
            "back_url": "hostel:rooms",
        },
    )


@login_required
@role_permission_required("change_room", "hostel")
def room_edit(request, pk):

    room = get_object_or_404(
        Room,
        pk=pk
    )

    form = RoomForm(
        request.POST or None,
        instance=room
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Room updated successfully."
        )

        return redirect("hostel:rooms")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Room",
            "subtitle": str(room),
            "back_url": "hostel:rooms",
        },
    )


# ============================================================
# BEDS
# ============================================================

@login_required
@role_permission_required("view_bed", "hostel")
def beds(request):

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    hostel_id = request.GET.get("hostel", "").strip()

    qs = Bed.objects.select_related(
        "room",
        "room__hostel",
    )

    if search:
        qs = qs.filter(
            Q(bed_number__icontains=search)
            | Q(room__room_number__icontains=search)
            | Q(room__hostel__name__icontains=search)
        )

    if status:
        qs = qs.filter(status=status)

    if hostel_id:
        qs = qs.filter(
            room__hostel_id=hostel_id
        )

    return render(
        request,
        "hostel/beds.html",
        {
            **branding_context(),
            "beds": qs,
            "hostels": Hostel.objects.filter(
                is_active=True
            ),
            "search": search,
            "status": status,
            "hostel_id": hostel_id,
            "status_choices": Bed.STATUS_CHOICES,
        },
    )


@login_required
@role_permission_required("add_bed", "hostel")
def bed_create(request):

    form = BedForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Bed created successfully."
        )

        return redirect("hostel:beds")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Add Bed",
            "subtitle": "Create a bed within a room",
            "back_url": "hostel:beds",
        },
    )


@login_required
@role_permission_required("change_bed", "hostel")
def bed_edit(request, pk):

    bed = get_object_or_404(
        Bed,
        pk=pk
    )

    form = BedForm(
        request.POST or None,
        instance=bed
    )

    if request.method == "POST" and form.is_valid():

        new_status = form.cleaned_data["status"]

        if new_status != "occupied":

            if StudentHostelAllocation.objects.filter(
                bed=bed,
                status="active"
            ).exists():

                messages.error(
                    request,
                    "This bed has an active student allocation. End or transfer the allocation first."
                )

                return redirect(
                    "hostel:bed_edit",
                    pk=bed.pk
                )

        form.save()

        messages.success(
            request,
            "Bed updated successfully."
        )

        return redirect("hostel:beds")

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Bed",
            "subtitle": str(bed),
            "back_url": "hostel:beds",
        },
    )


# ============================================================
# ALLOCATIONS
# ============================================================

@login_required
@role_permission_required("view_studenthostelallocation", "hostel")
def allocations(request):

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    qs = (
        StudentHostelAllocation.objects
        .select_related(
            "student",
            "hostel",
            "room",
            "bed",
        )
        .order_by("-admission_date", "-id")
    )

    if search:
        qs = qs.filter(
            Q(student__first_name__icontains=search)
            | Q(student__middle_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(student__admission_no__icontains=search)
            | Q(hostel__name__icontains=search)
            | Q(room__room_number__icontains=search)
        )

    if status:
        qs = qs.filter(status=status)

    return render(
        request,
        "hostel/allocations.html",
        {
            **branding_context(),
            "allocations": qs,
            "search": search,
            "status": status,
        },
    )


@login_required
@role_permission_required("add_studenthostelallocation", "hostel")
def allocation_create(request):

    form = AllocationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        with transaction.atomic():

            allocation = form.save()

            if allocation.bed:

                if allocation.status == "active":

                    allocation.bed.status = "occupied"
                    allocation.bed.save(
                        update_fields=["status"]
                    )

        messages.success(
            request,
            "Student hostel allocation created successfully."
        )

        return redirect(
            "hostel:allocations"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Allocate Student",
            "subtitle": "Place a learner in a hostel room and bed",
            "back_url": "hostel:allocations",
        },
    )


@login_required
@role_permission_required("change_studenthostelallocation", "hostel")
def allocation_edit(request, pk):

    allocation = get_object_or_404(
        StudentHostelAllocation.objects.select_related(
            "bed"
        ),
        pk=pk
    )

    old_bed = allocation.bed

    form = AllocationForm(
        request.POST or None,
        instance=allocation
    )

    if request.method == "POST" and form.is_valid():

        with transaction.atomic():

            updated = form.save()

            if old_bed and old_bed != updated.bed:

                if not StudentHostelAllocation.objects.filter(
                    bed=old_bed,
                    status="active"
                ).exclude(
                    pk=updated.pk
                ).exists():

                    old_bed.status = "available"
                    old_bed.save(
                        update_fields=["status"]
                    )

            if updated.bed:

                if updated.status == "active":

                    updated.bed.status = "occupied"
                    updated.bed.save(
                        update_fields=["status"]
                    )

                elif not StudentHostelAllocation.objects.filter(
                    bed=updated.bed,
                    status="active"
                ).exclude(
                    pk=updated.pk
                ).exists():

                    updated.bed.status = "available"
                    updated.bed.save(
                        update_fields=["status"]
                    )

        messages.success(
            request,
            "Allocation updated successfully."
        )

        return redirect(
            "hostel:allocations"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Allocation",
            "subtitle": str(allocation),
            "back_url": "hostel:allocations",
        },
    )


@login_required
@role_permission_required("change_studenthostelallocation", "hostel")
def allocation_end(request, pk):

    allocation = get_object_or_404(
        StudentHostelAllocation,
        pk=pk
    )

    if request.method == "POST":

        with transaction.atomic():

            allocation.status = "ended"
            allocation.leaving_date = date.today()
            allocation.save(
                update_fields=[
                    "status",
                    "leaving_date",
                    "updated_at",
                ]
            )

            if allocation.bed:

                if not StudentHostelAllocation.objects.filter(
                    bed=allocation.bed,
                    status="active"
                ).exists():

                    allocation.bed.status = "available"
                    allocation.bed.save(
                        update_fields=["status"]
                    )

        messages.success(
            request,
            "Student allocation ended and the bed is now available."
        )

    return redirect(
        "hostel:allocations"
    )


# ============================================================
# ATTENDANCE
# ============================================================

@login_required
@role_permission_required("view_hostelattendance", "hostel")
def attendance(request):

    selected_date = request.GET.get(
        "date"
    ) or request.POST.get(
        "date"
    ) or str(date.today())

    hostel_id = request.GET.get(
        "hostel"
    ) or request.POST.get(
        "hostel"
    ) or ""

    allocations = (
        StudentHostelAllocation.objects
        .filter(status="active")
        .select_related(
            "student",
            "hostel",
            "room",
            "bed",
        )
        .order_by(
            "hostel__name",
            "room__room_number",
            "student__first_name",
        )
    )

    if hostel_id:
        allocations = allocations.filter(
            hostel_id=hostel_id
        )

    if request.method == "POST":

        for allocation in allocations:

            status_value = request.POST.get(
                f"status_{allocation.student_id}"
            )

            remarks = request.POST.get(
                f"remarks_{allocation.student_id}",
                ""
            )

            if status_value:

                HostelAttendance.objects.update_or_create(
                    student=allocation.student,
                    date=selected_date,
                    defaults={
                        "hostel": allocation.hostel,
                        "status": status_value,
                        "remarks": remarks,
                    },
                )

        messages.success(
            request,
            f"Hostel attendance saved for {selected_date}."
        )

        return redirect(
            f"/hostel/attendance/?date={selected_date}"
            + (
                f"&hostel={hostel_id}"
                if hostel_id
                else ""
            )
        )

    attendance_map = {
        record.student_id: record
        for record in HostelAttendance.objects.filter(
            date=selected_date
        )
    }

    return render(
        request,
        "hostel/attendance.html",
        {
            **branding_context(),
            "allocations": allocations,
            "attendance_map": attendance_map,
            "hostels": Hostel.objects.filter(
                is_active=True
            ),
            "selected_date": selected_date,
            "hostel_id": hostel_id,
            "status_choices": HostelAttendance.STATUS_CHOICES,
        },
    )


# ============================================================
# FEES
# ============================================================

@login_required
@role_permission_required("view_hostelfee", "hostel")
def fees(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    qs = HostelFee.objects.select_related(
        "student",
        "hostel",
    )

    if search:

        qs = qs.filter(
            Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(student__admission_no__icontains=search)
            | Q(reference__icontains=search)
            | Q(hostel__name__icontains=search)
        )

    if status == "paid":
        qs = qs.filter(paid=True)

    elif status == "outstanding":
        qs = qs.filter(paid=False)

    outstanding = qs.filter(
        paid=False
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    return render(
        request,
        "hostel/fees.html",
        {
            **branding_context(),
            "fees": qs,
            "search": search,
            "status": status,
            "outstanding": outstanding,
        },
    )


@login_required
@role_permission_required("add_hostelfee", "hostel")
def fee_create(request):

    form = HostelFeeForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel fee record created successfully."
        )

        return redirect(
            "hostel:fees"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Add Hostel Fee",
            "subtitle": "Create a hostel charge",
            "back_url": "hostel:fees",
        },
    )


@login_required
@role_permission_required("change_hostelfee", "hostel")
def fee_edit(request, pk):

    fee = get_object_or_404(
        HostelFee,
        pk=pk
    )

    form = HostelFeeForm(
        request.POST or None,
        instance=fee
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel fee updated successfully."
        )

        return redirect(
            "hostel:fees"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Hostel Fee",
            "subtitle": str(fee),
            "back_url": "hostel:fees",
        },
    )


@login_required
@role_permission_required("change_hostelfee", "hostel")
def fee_mark_paid(request, pk):

    fee = get_object_or_404(
        HostelFee,
        pk=pk
    )

    if request.method == "POST":

        fee.paid = True
        fee.payment_date = date.today()

        fee.save(
            update_fields=[
                "paid",
                "payment_date",
            ]
        )

        messages.success(
            request,
            "Hostel fee marked as paid."
        )

    return redirect(
        "hostel:fees"
    )


# ============================================================
# INCIDENTS
# ============================================================

@login_required
@role_permission_required("view_hostelincident", "hostel")
def incidents(request):

    search = request.GET.get(
        "search",
        ""
    ).strip()

    severity = request.GET.get(
        "severity",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    qs = HostelIncident.objects.select_related(
        "student",
        "hostel",
    )

    if search:

        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(student__first_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(hostel__name__icontains=search)
        )

    if severity:
        qs = qs.filter(
            severity=severity
        )

    if status == "open":
        qs = qs.filter(
            resolved=False
        )

    elif status == "resolved":
        qs = qs.filter(
            resolved=True
        )

    return render(
        request,
        "hostel/incidents.html",
        {
            **branding_context(),
            "incidents": qs,
            "search": search,
            "severity": severity,
            "status": status,
            "severity_choices": HostelIncident.SEVERITY_CHOICES,
        },
    )


@login_required
@role_permission_required("add_hostelincident", "hostel")
def incident_create(request):

    form = HostelIncidentForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel incident recorded successfully."
        )

        return redirect(
            "hostel:incidents"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Report Hostel Incident",
            "subtitle": "Record a boarding incident",
            "back_url": "hostel:incidents",
        },
    )


@login_required
@role_permission_required("change_hostelincident", "hostel")
def incident_edit(request, pk):

    incident = get_object_or_404(
        HostelIncident,
        pk=pk
    )

    form = HostelIncidentForm(
        request.POST or None,
        instance=incident
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Hostel incident updated successfully."
        )

        return redirect(
            "hostel:incidents"
        )

    return render(
        request,
        "hostel/form.html",
        {
            **branding_context(),
            "form": form,
            "title": "Edit Incident",
            "subtitle": incident.title,
            "back_url": "hostel:incidents",
        },
    )


@login_required
@role_permission_required("change_hostelincident", "hostel")
def incident_resolve(request, pk):

    incident = get_object_or_404(
        HostelIncident,
        pk=pk
    )

    if request.method == "POST":

        incident.resolved = True

        incident.save(
            update_fields=["resolved"]
        )

        messages.success(
            request,
            "Incident marked as resolved."
        )

    return redirect(
        "hostel:incidents"
    )


# ============================================================
# HOSTEL APPLICATION MANAGEMENT
# ============================================================

@login_required
@role_permission_required("view_hostelapplication", "hostel")
def applications(request):

    from .models import HostelApplication

    search = request.GET.get(
        "search",
        "",
    ).strip()

    status = request.GET.get(
        "status",
        "",
    ).strip()

    applications = (
        HostelApplication.objects
        .select_related(
            "student",
            "hostel",
            "room",
        )
        .order_by("-created_at")
    )

    if search:
        applications = applications.filter(
            Q(student__first_name__icontains=search)
            | Q(student__middle_name__icontains=search)
            | Q(student__last_name__icontains=search)
            | Q(student__admission_no__icontains=search)
            | Q(hostel__name__icontains=search)
        )

    if status:
        applications = applications.filter(
            status=status
        )

    return render(
        request,
        "hostel/applications.html",
        {
            "applications": applications,
            "search": search,
            "status": status,
        },
    )


@login_required
@role_permission_required("change_hostelapplication", "hostel")
def application_approve(request, pk):

    from .models import HostelApplication

    application = get_object_or_404(
        HostelApplication,
        pk=pk,
    )

    if request.method == "POST":

        application.status = "approved"
        application.review_notes = request.POST.get(
            "review_notes",
            "",
        ).strip()
        application.reviewed_at = timezone.now()
        application.save()

        messages.success(
            request,
            f"Hostel application for {application.student} has been approved.",
        )

    return redirect(
        "hostel:applications"
    )


@login_required
@role_permission_required("change_hostelapplication", "hostel")
def application_reject(request, pk):

    from .models import HostelApplication

    application = get_object_or_404(
        HostelApplication,
        pk=pk,
    )

    if request.method == "POST":

        application.status = "rejected"
        application.review_notes = request.POST.get(
            "review_notes",
            "",
        ).strip()
        application.reviewed_at = timezone.now()
        application.save()

        messages.warning(
            request,
            f"Hostel application for {application.student} has been rejected.",
        )

    return redirect(
        "hostel:applications"
    )
