from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from students.models import Student
from timetable.legacy_compat import Subject

from .models import WeeklyAssessmentReport, WeeklyAssessmentWeek
from .views import _is_admin


def _parse_class(value):
    parts = (value or "").split("||", 1)

    class_name = parts[0].strip()
    stream = parts[1].strip() if len(parts) > 1 else ""

    return class_name, stream


def _admin_classes():
    rows = (
        Student.objects
        .filter(is_active=True)
        .values_list("class_name", "stream")
        .distinct()
        .order_by("class_name", "stream")
    )

    seen = set()
    result = []

    for class_name, stream in rows:

        class_name = (class_name or "").strip()
        stream = (stream or "").strip()

        if not class_name:
            continue

        key = (
            class_name.lower(),
            stream.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        result.append({
            "value": f"{class_name}||{stream}",
            "class_name": class_name,
            "stream": stream,
            "label": (
                f"{class_name} — {stream}"
                if stream
                else class_name
            ),
        })

    return result


def _admin_students(class_name="", stream=""):

    qs = Student.objects.filter(
        is_active=True
    )

    if class_name:
        qs = qs.filter(
            class_name__iexact=class_name
        )

    if stream:
        qs = qs.filter(
            stream__iexact=stream
        )

    return qs.order_by(
        "last_name",
        "first_name",
        "middle_name",
    )


@login_required
def admin_write(request):

    if not _is_admin(request.user):
        return HttpResponseForbidden(
            "Administrator access required."
        )

    weeks = (
        WeeklyAssessmentWeek.objects
        .select_related(
            "academic_year",
            "term",
        )
        .order_by(
            "-week_start",
            "-week_number",
        )
    )

    classes = _admin_classes()

    mode = request.GET.get(
        "mode",
        "",
    )

    context = {
        "portal": "admin",
        "mode": mode,

        "weeks": weeks,
        "classes": classes,

        "students": [],

        "subjects": Subject.objects.all().order_by(
            "name"
        ),

        "selected_class": "",
        "selected_stream": "",
        "selected_week": "",
        "selected_subject": "",
    }

    # -------------------------------------------------
    # INDIVIDUAL
    # -------------------------------------------------

    if mode == "individual":

        class_value = request.GET.get(
            "class",
            "",
        )

        week_id = request.GET.get(
            "week",
            "",
        )

        class_name, stream = _parse_class(
            class_value
        )

        context["selected_class"] = class_name
        context["selected_stream"] = stream
        context["selected_week"] = week_id

        if class_name:
            context["students"] = _admin_students(
                class_name,
                stream,
            )

    # -------------------------------------------------
    # WHOLE CLASS
    # -------------------------------------------------

    elif mode == "class":

        class_value = request.GET.get(
            "class",
            ""
        )

        week_id = request.GET.get(
            "week",
            ""
        )

        subject_id = request.GET.get(
            "subject",
            ""
        )

        class_name, stream = _parse_class(
            class_value
        )

        context["selected_class"] = class_name
        context["selected_stream"] = stream
        context["selected_week"] = week_id
        context["selected_subject"] = subject_id

        if class_name:
            context["students"] = _admin_students(
                class_name,
                stream,
            )

    return render(
        request,
        "weekly_reports/staff_write.html",
        context,
    )


@login_required
def admin_write_individual(request):

    if not _is_admin(request.user):
        return HttpResponseForbidden(
            "Administrator access required."
        )

    if request.method != "POST":
        return redirect(
            "weekly_reports:admin_write"
        )

    week_id = request.POST.get(
        "week",
        ""
    )

    student_id = request.POST.get(
        "student",
        ""
    )

    subject_id = request.POST.get(
        "subject",
        ""
    )

    score = request.POST.get(
        "score",
        "",
    ).strip()

    max_score = request.POST.get(
        "max_score",
        "100",
    ).strip()

    teacher_report = request.POST.get(
        "teacher_report",
        "",
    ).strip()

    week = get_object_or_404(
        WeeklyAssessmentWeek,
        pk=week_id,
    )

    student = get_object_or_404(
        Student,
        pk=student_id,
        is_active=True,
    )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
    )

    try:

        score_value = float(score)
        max_score_value = float(max_score)

        if max_score_value <= 0:
            raise ValueError

        if (
            score_value < 0
            or score_value > max_score_value
        ):
            raise ValueError

    except (TypeError, ValueError):

        messages.error(
            request,
            "Enter a valid score within the maximum score.",
        )

        return redirect(
            f"/weekly-reports/admin/write/"
            f"?mode=individual"
            f"&class={student.class_name}||{student.stream or ''}"
            f"&week={week.pk}"
        )

    WeeklyAssessmentReport.objects.update_or_create(

        student=student,

        subject=subject,

        week_start=week.week_start,

        week_end=week.week_end,

        defaults={

            "week": week,

            "class_name": (
                student.class_name or ""
            ),

            "stream": (
                student.stream or ""
            ),

            "week_number": week.week_number,

            "score": score_value,

            "max_score": max_score_value,

            "teacher_report": teacher_report,

            "created_by": request.user,

            "updated_by": request.user,
        },
    )

    messages.success(
        request,
        f"Weekly assessment saved for {student}.",
    )

    return redirect(
        f"/weekly-reports/admin/write/"
        f"?mode=individual"
        f"&class={student.class_name}||{student.stream or ''}"
        f"&week={week.pk}"
    )


@login_required
def admin_write_class(request):

    if not _is_admin(request.user):
        return HttpResponseForbidden(
            "Administrator access required."
        )

    if request.method != "POST":
        return redirect(
            "weekly_reports:admin_write"
        )

    class_value = request.POST.get(
        "class",
        ""
    )

    week_id = request.POST.get(
        "week",
        ""
    )

    subject_id = request.POST.get(
        "subject",
        ""
    )

    class_name, stream = _parse_class(
        class_value
    )

    week = get_object_or_404(
        WeeklyAssessmentWeek,
        pk=week_id,
    )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
    )

    students = _admin_students(
        class_name,
        stream,
    )

    saved = 0

    with transaction.atomic():

        for student in students:

            score = request.POST.get(
                f"score_{student.pk}",
                "",
            ).strip()

            if score == "":
                continue

            max_score = request.POST.get(
                f"max_score_{student.pk}",
                "100",
            ).strip()

            teacher_report = request.POST.get(
                f"report_{student.pk}",
                "",
            ).strip()

            try:

                score_value = float(score)
                max_score_value = float(max_score)

                if max_score_value <= 0:
                    continue

                if (
                    score_value < 0
                    or score_value > max_score_value
                ):
                    continue

            except (TypeError, ValueError):

                continue

            WeeklyAssessmentReport.objects.update_or_create(

                student=student,

                subject=subject,

                week_start=week.week_start,

                week_end=week.week_end,

                defaults={

                    "week": week,

                    "class_name": (
                        student.class_name or ""
                    ),

                    "stream": (
                        student.stream or ""
                    ),

                    "week_number": week.week_number,

                    "score": score_value,

                    "max_score": max_score_value,

                    "teacher_report": teacher_report,

                    "created_by": request.user,

                    "updated_by": request.user,
                },
            )

            saved += 1

    messages.success(
        request,
        f"{saved} weekly assessment reports saved.",
    )

    return redirect(
        f"/weekly-reports/admin/write/"
        f"?mode=class"
        f"&class={class_value}"
        f"&week={week.pk}"
        f"&subject={subject.pk}"
    )

