from datetime import datetime

from django.contrib.auth.decorators import login_required

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from students.models import Student
from accounts.models import SchoolBranding
from accounts.staff_access import (
    is_admin_user,
    get_staff_students,
    can_view_class,
    can_mark_attendance,
)
from .models import Attendance


# =========================================================
# ATTENDANCE DASHBOARD
# =========================================================

@login_required
def attendance_dashboard(request):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "view_attendance",
            "attendance",
        )
    ):
        return redirect("accounts:staff_dashboard")

    return render(
        request,
        "attendance/attendance_dashboard.html"
    )


# =========================================================
# RECORD ATTENDANCE
# =========================================================

@login_required
def mark_attendance(request):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "view_attendance",
            "attendance",
        )
    ):
        return redirect("accounts:staff_dashboard")

    allowed_students = get_staff_students(request.user)

    # -----------------------------------------------------
    # CLASSES AVAILABLE TO THIS USER
    # -----------------------------------------------------

    classes = (
        allowed_students
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    streams = (
        allowed_students
        .values_list("stream", flat=True)
        .distinct()
        .order_by("stream")
    )

    selected_class = request.GET.get(
        "class_name",
        ""
    ).strip()

    selected_stream = request.GET.get(
        "stream",
        ""
    ).strip()

    selected_date = request.GET.get(
        "attendance_date",
        str(timezone.localdate())
    ).strip()

    students = []

    # -----------------------------------------------------
    # LOAD STUDENTS
    # -----------------------------------------------------

    if selected_class and selected_stream:

        # Backend permission check.
        # This checks whether the teacher is assigned to
        # this class/stream at all.
        if not can_view_class(
            request.user,
            selected_class,
            selected_stream,
        ):

            messages.error(
                request,
                "You are not authorized to view this class."
            )

            return redirect(
                "attendance:mark_attendance"
            )

        students = (
            allowed_students
            .filter(
                class_name=selected_class,
                stream=selected_stream,
            )
            .order_by(
                "last_name",
                "first_name",
            )
        )

        existing_records = Attendance.objects.filter(
            date=selected_date,
            student__in=students,
        )

        attendance_map = {
            record.student_id: record
            for record in existing_records
        }

        for student in students:

            record = attendance_map.get(student.id)

            if record:

                student.attendance_status = record.status
                student.attendance_remarks = (
                    record.remarks or ""
                )

            else:

                student.attendance_status = "present"
                student.attendance_remarks = ""

    # -----------------------------------------------------
    # CAN CURRENT USER EDIT ATTENDANCE?
    # -----------------------------------------------------

    can_edit_attendance = False

    if selected_class and selected_stream:

        can_edit_attendance = can_mark_attendance(
            request.user,
            selected_class,
            selected_stream,
        )

    context = {
        "classes": classes,
        "streams": streams,
        "students": students,
        "selected_class": selected_class,
        "selected_stream": selected_stream,
        "selected_date": selected_date,
        "can_edit_attendance": can_edit_attendance,
    }

    return render(
        request,
        "attendance/mark_attendance.html",
        context,
    )


# =========================================================
# SAVE ATTENDANCE
# =========================================================

@login_required
def save_attendance(request):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "add_attendance",
            "attendance",
        )
        or user_has_role_permission(
            request.user,
            "change_attendance",
            "attendance",
        )
    ):
        messages.error(
            request,
            "You are not authorized to record attendance."
        )
        return redirect("attendance:dashboard")

    if request.method != "POST":

        messages.error(
            request,
            "Invalid attendance submission."
        )

        return redirect(
            "attendance:mark_attendance"
        )

    class_name = request.POST.get(
        "class_name",
        ""
    ).strip()

    stream = request.POST.get(
        "stream",
        ""
    ).strip()

    attendance_date = request.POST.get(
        "attendance_date",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not class_name or not stream or not attendance_date:

        messages.error(
            request,
            "Please select class, stream and attendance date."
        )

        return redirect(
            "attendance:mark_attendance"
        )

    try:

        datetime.strptime(
            attendance_date,
            "%Y-%m-%d"
        )

    except ValueError:

        messages.error(
            request,
            "Invalid attendance date."
        )

        return redirect(
            "attendance:mark_attendance"
        )

    # -----------------------------------------------------
    # IMPORTANT SECURITY CHECK
    #
    # Only:
    #   ADMIN
    #   CLASS TEACHER
    #
    # can write attendance.
    #
    # Subject teachers may view the register but cannot
    # submit attendance.
    # -----------------------------------------------------

    if not can_mark_attendance(
        request.user,
        class_name,
        stream,
    ):

        messages.error(
            request,
            "You are not authorized to record attendance "
            "for this class and stream."
        )

        return redirect(
            "attendance:mark_attendance"
        )

    # -----------------------------------------------------
    # GET ONLY AUTHORIZED LEARNERS
    # -----------------------------------------------------

    students = (
        get_staff_students(request.user)
        .filter(
            class_name=class_name,
            stream=stream,
        )
        .order_by(
            "last_name",
            "first_name",
        )
    )

    # -----------------------------------------------------
    # SECONDARY SECURITY CHECK
    # -----------------------------------------------------

    if not is_admin_user(request.user) and not students.exists():

        messages.error(
            request,
            "No learners were found for your assigned class."
        )

        return redirect(
            "attendance:mark_attendance"
        )

    saved_count = 0

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    for student in students:

        status = request.POST.get(
            f"status_{student.id}",
            ""
        ).strip()

        remarks = request.POST.get(
            f"remarks_{student.id}",
            ""
        ).strip()

        if status not in (
            "present",
            "absent",
            "late",
            "excused",
        ):
            continue

        Attendance.objects.update_or_create(
            student=student,
            date=attendance_date,
            defaults={
                "status": status,
                "remarks": remarks,
            },
        )

        saved_count += 1

    # -----------------------------------------------------
    # MESSAGE
    # -----------------------------------------------------

    if saved_count:

        messages.success(
            request,
            f"Attendance saved successfully for "
            f"{saved_count} learners."
        )

    else:

        messages.warning(
            request,
            "No attendance records were submitted."
        )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return redirect(
        f"/attendance/mark/"
        f"?class_name={class_name}"
        f"&stream={stream}"
        f"&attendance_date={attendance_date}"
    )


# =========================================================
# VIEW ATTENDANCE
# =========================================================

@login_required
def view_attendance(request):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "view_attendance",
            "attendance",
        )
    ):
        return redirect("accounts:staff_dashboard")

    allowed_students = get_staff_students(request.user)

    classes = (
        allowed_students
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    streams = (
        allowed_students
        .values_list("stream", flat=True)
        .distinct()
        .order_by("stream")
    )

    selected_class = request.GET.get(
        "class_name",
        ""
    ).strip()

    selected_stream = request.GET.get(
        "stream",
        ""
    ).strip()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    # -----------------------------------------------------
    # CLASS ACCESS CHECK
    # -----------------------------------------------------

    if selected_class and selected_stream:

        if not can_view_class(
            request.user,
            selected_class,
            selected_stream,
        ):

            messages.error(
                request,
                "You are not authorized to view this class."
            )

            return redirect(
                "attendance:view_attendance"
            )

    # -----------------------------------------------------
    # BASE QUERY
    # -----------------------------------------------------

    records = (
        Attendance.objects
        .select_related("student")
        .filter(student__in=allowed_students)
    )

    # -----------------------------------------------------
    # CLASS FILTER
    # -----------------------------------------------------

    if selected_class:

        records = records.filter(
            student__class_name=selected_class
        )

    # -----------------------------------------------------
    # STREAM FILTER
    # -----------------------------------------------------

    if selected_stream:

        records = records.filter(
            student__stream=selected_stream
        )

    # -----------------------------------------------------
    # DATE FROM
    # -----------------------------------------------------

    if date_from:

        try:

            datetime.strptime(
                date_from,
                "%Y-%m-%d"
            )

            records = records.filter(
                date__gte=date_from
            )

        except ValueError:

            date_from = ""

    # -----------------------------------------------------
    # DATE TO
    # -----------------------------------------------------

    if date_to:

        try:

            datetime.strptime(
                date_to,
                "%Y-%m-%d"
            )

            records = records.filter(
                date__lte=date_to
            )

        except ValueError:

            date_to = ""

    # -----------------------------------------------------
    # ORDER
    # -----------------------------------------------------

    records = records.order_by(
        "-date",
        "student__class_name",
        "student__stream",
        "student__last_name",
        "student__first_name",
    )

    # =====================================================
    # ATTENDANCE ANALYSIS
    # =====================================================

    total_records = records.count()

    present_count = records.filter(
        status="present"
    ).count()

    absent_count = records.filter(
        status="absent"
    ).count()

    late_count = records.filter(
        status="late"
    ).count()

    excused_count = records.filter(
        status="excused"
    ).count()

    attendance_percentage = 0

    if total_records > 0:

        attendance_percentage = round(
            (
                (
                    present_count
                    + late_count
                )
                / total_records
            ) * 100,
            1
        )

    absence_percentage = 0

    if total_records > 0:

        absence_percentage = round(
            (
                absent_count
                / total_records
            ) * 100,
            1
        )

    late_percentage = 0

    if total_records > 0:

        late_percentage = round(
            (
                late_count
                / total_records
            ) * 100,
            1
        )

    excused_percentage = 0

    if total_records > 0:

        excused_percentage = round(
            (
                excused_count
                / total_records
            ) * 100,
            1
        )

    context = {

        "classes": classes,
        "streams": streams,

        "selected_class": selected_class,
        "selected_stream": selected_stream,

        "date_from": date_from,
        "date_to": date_to,

        "records": records,

        "total": total_records,
        "total_records": total_records,

        "present": present_count,
        "present_count": present_count,

        "absent": absent_count,
        "absent_count": absent_count,

        "late": late_count,
        "late_count": late_count,

        "excused": excused_count,
        "excused_count": excused_count,

        "attendance_percentage": attendance_percentage,
        "absence_percentage": absence_percentage,
        "late_percentage": late_percentage,
        "excused_percentage": excused_percentage,
    }

    return render(
        request,
        "attendance/view_attendance.html",
        context,
    )


# =========================================================
# PRINT ATTENDANCE
# =========================================================

@login_required
def print_attendance(request):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "view_attendance",
            "attendance",
        )
    ):
        return redirect("accounts:staff_dashboard")

    allowed_students = get_staff_students(request.user)

    selected_class = request.GET.get(
        "class_name",
        ""
    ).strip()

    selected_stream = request.GET.get(
        "stream",
        ""
    ).strip()

    date_from = request.GET.get(
        "date_from",
        ""
    ).strip()

    date_to = request.GET.get(
        "date_to",
        ""
    ).strip()

    # -----------------------------------------------------
    # CLASS ACCESS CHECK
    # -----------------------------------------------------

    if selected_class and selected_stream:

        if not can_view_class(
            request.user,
            selected_class,
            selected_stream,
        ):

            messages.error(
                request,
                "You are not authorized to print this class."
            )

            return redirect(
                "attendance:view_attendance"
            )

    records = (
        Attendance.objects
        .select_related("student")
        .filter(student__in=allowed_students)
    )

    if selected_class:

        records = records.filter(
            student__class_name=selected_class
        )

    if selected_stream:

        records = records.filter(
            student__stream=selected_stream
        )

    if date_from:

        records = records.filter(
            date__gte=date_from
        )

    if date_to:

        records = records.filter(
            date__lte=date_to
        )

    records = records.order_by(
        "student__class_name",
        "student__stream",
        "student__last_name",
        "student__first_name",
        "date",
    )

    total_records = records.count()

    present_count = records.filter(
        status="present"
    ).count()

    absent_count = records.filter(
        status="absent"
    ).count()

    late_count = records.filter(
        status="late"
    ).count()

    excused_count = records.filter(
        status="excused"
    ).count()

    attendance_percentage = 0

    if total_records:

        attendance_percentage = round(
            (
                (
                    present_count
                    + late_count
                )
                / total_records
            ) * 100,
            1
        )

    absence_percentage = 0

    if total_records:

        absence_percentage = round(
            (
                absent_count
                / total_records
            ) * 100,
            1
        )

    branding = (
        SchoolBranding.objects
        .filter(is_active=True)
        .order_by("-id")
        .first()
    )

    context = {

        "branding": branding,

        "records": records,

        "selected_class": selected_class,

        "selected_stream": selected_stream,

        "date_from": date_from,

        "date_to": date_to,

        "total": total_records,

        "total_records": total_records,

        "present": present_count,

        "present_count": present_count,

        "absent": absent_count,

        "absent_count": absent_count,

        "late": late_count,

        "late_count": late_count,

        "excused": excused_count,

        "excused_count": excused_count,

        "attendance_percentage": attendance_percentage,

        "absence_percentage": absence_percentage,
    }

    return render(
        request,
        "attendance/attendance_print.html",
        context,
    )


# =========================================================
# CLASS ATTENDANCE
# =========================================================

@login_required
def class_attendance(
    request,
    class_name
):

    from accounts.views import user_has_role_permission

    if not (
        is_admin_user(request.user)
        or user_has_role_permission(
            request.user,
            "view_attendance",
            "attendance",
        )
    ):
        return redirect("accounts:staff_dashboard")

    students = (
        get_staff_students(request.user)
        .filter(
            class_name=class_name
        )
        .order_by(
            "stream",
            "last_name",
            "first_name",
        )
    )

    # -----------------------------------------------------
    # SECURITY CHECK
    # -----------------------------------------------------

    if not is_admin_user(request.user) and not students.exists():

        messages.error(
            request,
            "You are not authorized to view this class."
        )

        return redirect(
            "attendance:dashboard"
        )

    context = {
        "students": students,
        "class_name": class_name,
    }

    return render(
        request,
        "attendance/class_attendance.html",
        context,
    )



