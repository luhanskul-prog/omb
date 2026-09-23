from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q

from students.models import Student
from .models import Attendance


# ============================================================
# ATTENDANCE DASHBOARD
# ============================================================

@login_required
def attendance_dashboard(request):

    total_records = Attendance.objects.count()

    present_count = Attendance.objects.filter(
        status="PRESENT"
    ).count()

    absent_count = Attendance.objects.filter(
        status="ABSENT"
    ).count()

    late_count = Attendance.objects.filter(
        status="LATE"
    ).count()

    excused_count = Attendance.objects.filter(
        status="EXCUSED"
    ).count()

    context = {
        "total_records": total_records,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "excused_count": excused_count,
    }

    return render(
        request,
        "school_attendance/attendance_dashboard.html",
        context
    )


# ============================================================
# DAILY ATTENDANCE
# ============================================================

@login_required
def daily_attendance(request):

    # ---------------------------------------------------------
    # GET CLASSES DIRECTLY FROM STUDENT RECORDS
    # ---------------------------------------------------------

    classes = (
        Student.objects
        .exclude(class_name__isnull=True)
        .exclude(class_name__exact="")
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
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
        "date",
        date.today().isoformat()
    )

    streams = []

    learners = Student.objects.none()

    # ---------------------------------------------------------
    # LOAD STREAMS
    # ---------------------------------------------------------

    if selected_class:

        streams = (
            Student.objects
            .filter(class_name=selected_class)
            .exclude(stream__isnull=True)
            .exclude(stream__exact="")
            .values_list("stream", flat=True)
            .distinct()
            .order_by("stream")
        )

    # ---------------------------------------------------------
    # LOAD LEARNERS
    # ---------------------------------------------------------

    if selected_class and selected_stream:

        learners = (
            Student.objects
            .filter(
                class_name=selected_class,
                stream=selected_stream
            )
            .order_by(
                "first_name",
                "middle_name",
                "last_name"
            )
        )

    # ---------------------------------------------------------
    # SAVE ATTENDANCE
    # ---------------------------------------------------------

    if request.method == "POST":

        selected_class = request.POST.get(
            "class_name",
            ""
        ).strip()

        selected_stream = request.POST.get(
            "stream",
            ""
        ).strip()

        selected_date = request.POST.get(
            "date",
            ""
        ).strip()

        if (
            not selected_class
            or not selected_stream
            or not selected_date
        ):

            messages.error(
                request,
                "Please select a class, stream and date."
            )

            return redirect(
                "school_attendance:daily_attendance"
            )

        learners = (
            Student.objects
            .filter(
                class_name=selected_class,
                stream=selected_stream
            )
            .order_by(
                "first_name",
                "middle_name",
                "last_name"
            )
        )

        saved_count = 0

        valid_statuses = {
            "PRESENT",
            "ABSENT",
            "LATE",
            "EXCUSED",
        }

        for learner in learners:

            status = request.POST.get(
                f"status_{learner.id}",
                "PRESENT"
            )

            if status not in valid_statuses:
                status = "PRESENT"

            remarks = request.POST.get(
                f"remarks_{learner.id}",
                ""
            ).strip()

            Attendance.objects.update_or_create(
                student=learner,
                date=selected_date,
                defaults={
                    "status": status,
                    "remarks": remarks,
                }
            )

            saved_count += 1

        messages.success(
            request,
            f"Attendance saved successfully for "
            f"{saved_count} learners."
        )

        return redirect(
            f"/attendance/daily/"
            f"?class_name={selected_class}"
            f"&stream={selected_stream}"
            f"&date={selected_date}"
        )

    # ---------------------------------------------------------
    # EXISTING ATTENDANCE
    # ---------------------------------------------------------

    attendance_records = {}

    if learners and selected_date:

        records = Attendance.objects.filter(
            student__in=learners,
            date=selected_date
        )

        attendance_records = {
            record.student_id: record
            for record in records
        }

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "classes": classes,
        "streams": streams,
        "learners": learners,
        "attendance_records": attendance_records,
        "selected_class": selected_class,
        "selected_stream": selected_stream,
        "selected_date": selected_date,
    }

    return render(
        request,
        "school_attendance/daily_attendance.html",
        context
    )


# ============================================================
# ATTENDANCE REPORTS
# ============================================================

@login_required
def attendance_reports(request):

    # ---------------------------------------------------------
    # CLASSES FROM STUDENT SYSTEM
    # ---------------------------------------------------------

    classes = (
        Student.objects
        .exclude(class_name__isnull=True)
        .exclude(class_name__exact="")
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    # ---------------------------------------------------------
    # FILTERS
    # ---------------------------------------------------------

    selected_class = request.GET.get(
        "class_name",
        ""
    ).strip()

    selected_stream = request.GET.get(
        "stream",
        ""
    ).strip()

    start_date = request.GET.get(
        "start_date",
        ""
    ).strip()

    end_date = request.GET.get(
        "end_date",
        ""
    ).strip()

    # ---------------------------------------------------------
    # DEFAULT DATE RANGE
    # ---------------------------------------------------------

    if not start_date:
        start_date = date.today().isoformat()

    if not end_date:
        end_date = date.today().isoformat()

    # ---------------------------------------------------------
    # STREAMS FROM STUDENT SYSTEM
    # ---------------------------------------------------------

    streams = []

    if selected_class:

        streams = (
            Student.objects
            .filter(class_name=selected_class)
            .exclude(stream__isnull=True)
            .exclude(stream__exact="")
            .values_list("stream", flat=True)
            .distinct()
            .order_by("stream")
        )

    # ---------------------------------------------------------
    # ATTENDANCE RECORDS
    # ---------------------------------------------------------

    records = (
        Attendance.objects
        .select_related("student")
        .all()
    )

    if selected_class:

        records = records.filter(
            student__class_name=selected_class
        )

    if selected_stream:

        records = records.filter(
            student__stream=selected_stream
        )

    records = records.filter(
        date__gte=start_date,
        date__lte=end_date
    )

    records = records.order_by(
        "-date",
        "student__first_name",
        "student__middle_name",
        "student__last_name"
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    total_records = records.count()

    present_count = records.filter(
        status="PRESENT"
    ).count()

    absent_count = records.filter(
        status="ABSENT"
    ).count()

    late_count = records.filter(
        status="LATE"
    ).count()

    excused_count = records.filter(
        status="EXCUSED"
    ).count()

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "classes": classes,
        "streams": streams,
        "records": records,
        "attendance_records": records,

        "selected_class": selected_class,
        "selected_stream": selected_stream,

        "start_date": start_date,
        "end_date": end_date,

        "total_records": total_records,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "excused_count": excused_count,
    }

    return render(
        request,
        "school_attendance/attendance_reports.html",
        context
    )


# ============================================================
# ATTENDANCE ANALYSIS
# ============================================================

@login_required
def attendance_analysis(request):

    # ---------------------------------------------------------
    # CLASSES DIRECTLY FROM STUDENT SYSTEM
    # ---------------------------------------------------------

    classes = (
        Student.objects
        .exclude(class_name__isnull=True)
        .exclude(class_name__exact="")
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    # ---------------------------------------------------------
    # SELECTED FILTERS
    # ---------------------------------------------------------

    selected_class = request.GET.get(
        "class_name",
        ""
    ).strip()

    selected_stream = request.GET.get(
        "stream",
        ""
    ).strip()

    start_date = request.GET.get(
        "start_date",
        ""
    ).strip()

    end_date = request.GET.get(
        "end_date",
        ""
    ).strip()

    # ---------------------------------------------------------
    # DEFAULT DATE RANGE
    # LAST 30 DAYS
    # ---------------------------------------------------------

    if not start_date:

        start_date = (
            date.today() - timedelta(days=30)
        ).isoformat()

    if not end_date:

        end_date = date.today().isoformat()

    # ---------------------------------------------------------
    # STREAMS FROM STUDENT SYSTEM
    # ---------------------------------------------------------

    streams = []

    if selected_class:

        streams = (
            Student.objects
            .filter(class_name=selected_class)
            .exclude(stream__isnull=True)
            .exclude(stream__exact="")
            .values_list("stream", flat=True)
            .distinct()
            .order_by("stream")
        )

    # =========================================================
    # IMPORTANT:
    # GET LEARNERS DIRECTLY FROM STUDENT MODEL
    # =========================================================

    learners_queryset = (
        Student.objects
        .all()
    )

    # ---------------------------------------------------------
    # FILTER LEARNERS BY CLASS
    # ---------------------------------------------------------

    if selected_class:

        learners_queryset = learners_queryset.filter(
            class_name=selected_class
        )

    # ---------------------------------------------------------
    # FILTER LEARNERS BY STREAM
    # ---------------------------------------------------------

    if selected_stream:

        learners_queryset = learners_queryset.filter(
            stream=selected_stream
        )

    # ---------------------------------------------------------
    # ORDER LEARNERS
    # ---------------------------------------------------------

    learners_queryset = learners_queryset.order_by(
        "class_name",
        "stream",
        "first_name",
        "middle_name",
        "last_name"
    )

    # =========================================================
    # ATTENDANCE RECORDS FOR THE SELECTED PERIOD
    # =========================================================

    records = (
        Attendance.objects
        .select_related("student")
        .filter(
            date__gte=start_date,
            date__lte=end_date
        )
    )

    # ---------------------------------------------------------
    # FILTER RECORDS BY CLASS
    # ---------------------------------------------------------

    if selected_class:

        records = records.filter(
            student__class_name=selected_class
        )

    # ---------------------------------------------------------
    # FILTER RECORDS BY STREAM
    # ---------------------------------------------------------

    if selected_stream:

        records = records.filter(
            student__stream=selected_stream
        )

    # =========================================================
    # OVERALL COUNTS
    # =========================================================

    total_records = records.count()

    present_count = records.filter(
        status="PRESENT"
    ).count()

    absent_count = records.filter(
        status="ABSENT"
    ).count()

    late_count = records.filter(
        status="LATE"
    ).count()

    excused_count = records.filter(
        status="EXCUSED"
    ).count()

    # ---------------------------------------------------------
    # OVERALL ATTENDANCE PERCENTAGE
    # ---------------------------------------------------------

    if total_records > 0:

        attendance_percentage = round(
            (
                present_count
                / total_records
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    # =========================================================
    # LEARNER ANALYSIS
    # =========================================================

    learner_analysis = []

    for learner in learners_queryset:

        learner_records = records.filter(
            student=learner
        )

        total = learner_records.count()

        present = learner_records.filter(
            status="PRESENT"
        ).count()

        absent = learner_records.filter(
            status="ABSENT"
        ).count()

        late = learner_records.filter(
            status="LATE"
        ).count()

        excused = learner_records.filter(
            status="EXCUSED"
        ).count()

        # -----------------------------------------------------
        # ATTENDANCE PERCENTAGE
        # -----------------------------------------------------

        if total > 0:

            percentage = round(
                (present / total) * 100,
                2
            )

        else:

            percentage = 0

        # -----------------------------------------------------
        # ADD LEARNER
        # -----------------------------------------------------

        learner_analysis.append({

            "student": learner,

            "admission_no": learner.admission_no,

            "name": (
                f"{learner.first_name} "
                f"{learner.middle_name or ''} "
                f"{learner.last_name or ''}"
            ).strip(),

            "class_name": learner.class_name,

            "stream": learner.stream,

            "total": total,

            "present": present,

            "absent": absent,

            "late": late,

            "excused": excused,

            "percentage": percentage,

        })

    # =========================================================
    # CLASS ANALYSIS
    # =========================================================

    class_analysis = (
        records
        .values("student__class_name")
        .annotate(
            total=Count("id"),

            present=Count(
                "id",
                filter=Q(
                    status="PRESENT"
                )
            ),

            absent=Count(
                "id",
                filter=Q(
                    status="ABSENT"
                )
            ),

            late=Count(
                "id",
                filter=Q(
                    status="LATE"
                )
            ),

            excused=Count(
                "id",
                filter=Q(
                    status="EXCUSED"
                )
            ),
        )
        .order_by(
            "student__class_name"
        )
    )

    # ---------------------------------------------------------
    # CALCULATE CLASS PERCENTAGES
    # ---------------------------------------------------------

    for item in class_analysis:

        if item["total"]:

            item["percentage"] = round(
                (
                    item["present"]
                    / item["total"]
                ) * 100,
                2
            )

        else:

            item["percentage"] = 0

    # =========================================================
    # STREAM ANALYSIS
    # =========================================================

    stream_analysis = (
        records
        .values(
            "student__class_name",
            "student__stream"
        )
        .annotate(

            total=Count("id"),

            present=Count(
                "id",
                filter=Q(
                    status="PRESENT"
                )
            ),

            absent=Count(
                "id",
                filter=Q(
                    status="ABSENT"
                )
            ),

            late=Count(
                "id",
                filter=Q(
                    status="LATE"
                )
            ),

            excused=Count(
                "id",
                filter=Q(
                    status="EXCUSED"
                )
            ),
        )
        .order_by(
            "student__class_name",
            "student__stream"
        )
    )

    # ---------------------------------------------------------
    # STREAM PERCENTAGES
    # ---------------------------------------------------------

    for item in stream_analysis:

        if item["total"]:

            item["percentage"] = round(
                (
                    item["present"]
                    / item["total"]
                ) * 100,
                2
            )

        else:

            item["percentage"] = 0

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "classes": classes,

        "streams": streams,

        "selected_class": selected_class,

        "selected_stream": selected_stream,

        "start_date": start_date,

        "end_date": end_date,

        "total_records": total_records,

        "present_count": present_count,

        "absent_count": absent_count,

        "late_count": late_count,

        "excused_count": excused_count,

        "attendance_percentage": attendance_percentage,

        "learner_analysis": learner_analysis,

        "class_analysis": class_analysis,

        "stream_analysis": stream_analysis,

    }

    return render(
        request,
        "school_attendance/attendance_analysis.html",
        context
    )