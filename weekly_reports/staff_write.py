
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django import forms

from students.models import Student
from timetable.legacy_compat import Subject, TeacherTeachingAssignment
from .models import WeeklyAssessmentReport, WeeklyAssessmentWeek

from .views import (
    _is_staff,
    _is_admin,
    get_staff_teacher,
    is_class_teacher_for,
)


def _teacher_classes(user):
    teacher = get_staff_teacher(user)
    if not teacher:
        return []

    assignments = (
        TeacherTeachingAssignment.objects
        .filter(teacher=teacher, is_active=True)
        .order_by("class_name", "stream")
    )

    seen = set()
    result = []

    for a in assignments:
        cls = (a.class_name or "").strip()
        stream = (a.stream or "").strip()

        if not cls:
            continue

        key = (cls.lower(), stream.lower())

        if key in seen:
            continue

        seen.add(key)

        result.append({
            "value": f"{cls}||{stream}",
            "class_name": cls,
            "stream": stream,
            "label": f"{cls} — {stream}" if stream else cls,
        })

    return result


def _parse_class(value):
    parts = (value or "").split("||", 1)
    class_name = parts[0].strip()

    stream = parts[1].strip() if len(parts) > 1 else ""

    return class_name, stream


def _teacher_can_class(user, class_name, stream=""):
    teacher = get_staff_teacher(user)

    if not teacher or not class_name:
        return False

    try:
        if is_class_teacher_for(user, class_name):
            return True
    except Exception:
        pass

    qs = TeacherTeachingAssignment.objects.filter(
        teacher=teacher,
        class_name__iexact=class_name,
        is_active=True,
    )

    learner_stream = (stream or "").strip().lower()

    for assignment in qs:
        assigned_stream = (assignment.stream or "").strip().lower()

        if not assigned_stream or assigned_stream == learner_stream:
            return True

    return False


def _teacher_subjects(user, class_name, stream=""):
    teacher = get_staff_teacher(user)

    if not teacher:
        return Subject.objects.none()

    try:
        if is_class_teacher_for(user, class_name):
            return Subject.objects.all().order_by("name")
    except Exception:
        pass

    qs = TeacherTeachingAssignment.objects.filter(
        teacher=teacher,
        class_name__iexact=class_name,
        is_active=True,
    )

    subject_ids = []

    learner_stream = (stream or "").strip().lower()

    for assignment in qs:
        assigned_stream = (assignment.stream or "").strip().lower()

        if not assigned_stream or assigned_stream == learner_stream:
            subject_ids.append(assignment.subject_id)

    return Subject.objects.filter(
        pk__in=subject_ids
    ).order_by("name")


def _students_for_class(user, class_name, stream=""):
    if not _teacher_can_class(user, class_name, stream):
        return Student.objects.none()

    qs = Student.objects.filter(
        is_active=True,
        class_name__iexact=class_name,
    )

    if stream:
        qs = qs.filter(stream__iexact=stream)

    return qs.order_by("last_name", "first_name")


@login_required
def staff_write(request):

    if not _is_staff(request.user):
        return HttpResponseForbidden(
            "Teaching staff access required."
        )

    weeks = (
        WeeklyAssessmentWeek.objects
        .filter(is_locked=False)
        .select_related("academic_year", "term")
        .order_by("-week_start", "-week_number")
    )

    classes = _teacher_classes(request.user)

    mode = request.GET.get("mode", "")

    context = {
        "portal": "staff",
        "mode": mode,
        "weeks": weeks,
        "classes": classes,
        "students": [],
        "subjects": [],
        "selected_class": "",
        "selected_stream": "",
        "selected_week": "",
        "selected_subject": "",
    }

    if mode == "individual":

        class_value = request.GET.get("class", "")
        week_id = request.GET.get("week", "")

        class_name, stream = _parse_class(class_value)

        context["selected_class"] = class_name
        context["selected_stream"] = stream
        context["selected_week"] = week_id

        if class_name and _teacher_can_class(
            request.user,
            class_name,
            stream,
        ):
            context["students"] = _students_for_class(
                request.user,
                class_name,
                stream,
            )

        context["subjects"] = _teacher_subjects(
            request.user,
            class_name,
            stream,
        )

    elif mode == "class":

        class_value = request.GET.get("class", "")
        week_id = request.GET.get("week", "")
        subject_id = request.GET.get("subject", "")

        class_name, stream = _parse_class(class_value)

        context["selected_class"] = class_name
        context["selected_stream"] = stream
        context["selected_week"] = week_id
        context["selected_subject"] = subject_id

        if class_name and _teacher_can_class(
            request.user,
            class_name,
            stream,
        ):

            context["subjects"] = _teacher_subjects(
                request.user,
                class_name,
                stream,
            )

            if subject_id:
                allowed_subject_ids = set(
                    context["subjects"].values_list(
                        "id",
                        flat=True,
                    )
                )

                if int(subject_id) in allowed_subject_ids:
                    context["students"] = _students_for_class(
                        request.user,
                        class_name,
                        stream,
                    )

    return render(
        request,
        "weekly_reports/staff_write.html",
        context,
    )


@login_required
def staff_write_individual(request):

    if not _is_staff(request.user):
        return HttpResponseForbidden(
            "Teaching staff access required."
        )

    if request.method != "POST":
        return redirect("weekly_reports:staff_write")

    class_value = request.POST.get("class", "")
    week_id = request.POST.get("week", "")
    student_id = request.POST.get("student", "")
    subject_id = request.POST.get("subject", "")

    score = request.POST.get("score", "")
    max_score = request.POST.get("max_score", "100")
    teacher_report = request.POST.get("teacher_report", "")

    class_name, stream = _parse_class(class_value)

    if not _teacher_can_class(
        request.user,
        class_name,
        stream,
    ):
        return HttpResponseForbidden(
            "You are not assigned to this class."
        )

    week = get_object_or_404(
        WeeklyAssessmentWeek,
        pk=week_id,
    )

    if week.is_locked:
        return HttpResponseForbidden(
            "This assessment week is locked."
        )

    student = get_object_or_404(
        Student,
        pk=student_id,
        is_active=True,
        class_name__iexact=class_name,
    )

    if stream and (student.stream or "").strip().lower() != stream.lower():
        return HttpResponseForbidden(
            "This learner is not in the selected stream."
        )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
    )

    allowed_subject_ids = set(
        _teacher_subjects(
            request.user,
            class_name,
            stream,
        ).values_list("id", flat=True)
    )

    if subject.pk not in allowed_subject_ids:
        return HttpResponseForbidden(
            "You are not assigned to this subject."
        )

    try:
        score_value = float(score)
        max_score_value = float(max_score)

        if max_score_value <= 0:
            raise ValueError

        if score_value < 0 or score_value > max_score_value:
            raise ValueError

    except (TypeError, ValueError):
        messages.error(
            request,
            "Enter a valid score within the maximum score.",
        )
        return redirect(
            f"/weekly-reports/staff/write/?mode=individual"
            f"&class={class_value}&week={week_id}"
        )

    WeeklyAssessmentReport.objects.update_or_create(
        student=student,
        subject=subject,
        week_start=week.week_start,
        week_end=week.week_end,
        defaults={
            "week": week,
            "class_name": student.class_name or "",
            "stream": student.stream or "",
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
        f"Weekly report saved for {student}.",
    )

    return redirect(
        f"/weekly-reports/staff/write/?mode=individual"
        f"&class={class_value}&week={week_id}"
    )


@login_required
def staff_write_class(request):

    if not _is_staff(request.user):
        return HttpResponseForbidden(
            "Teaching staff access required."
        )

    if request.method != "POST":
        return redirect("weekly_reports:staff_write")

    class_value = request.POST.get("class", "")
    week_id = request.POST.get("week", "")
    subject_id = request.POST.get("subject", "")

    class_name, stream = _parse_class(class_value)

    if not _teacher_can_class(
        request.user,
        class_name,
        stream,
    ):
        return HttpResponseForbidden(
            "You are not assigned to this class."
        )

    week = get_object_or_404(
        WeeklyAssessmentWeek,
        pk=week_id,
    )

    if week.is_locked:
        return HttpResponseForbidden(
            "This assessment week is locked."
        )

    subject = get_object_or_404(
        Subject,
        pk=subject_id,
    )

    allowed_subject_ids = set(
        _teacher_subjects(
            request.user,
            class_name,
            stream,
        ).values_list("id", flat=True)
    )

    if subject.pk not in allowed_subject_ids:
        return HttpResponseForbidden(
            "You are not assigned to this subject."
        )

    students = _students_for_class(
        request.user,
        class_name,
        stream,
    )

    with transaction.atomic():

        for student in students:

            score = request.POST.get(
                f"score_{student.pk}",
                "",
            ).strip()

            teacher_report = request.POST.get(
                f"report_{student.pk}",
                "",
            ).strip()

            if score == "":
                continue

            max_score = request.POST.get(
                f"max_score_{student.pk}",
                "100",
            ).strip()

            try:
                score_value = float(score)
                max_score_value = float(max_score)

                if max_score_value <= 0:
                    continue

                if score_value < 0 or score_value > max_score_value:
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
                    "class_name": student.class_name or "",
                    "stream": student.stream or "",
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
        f"Reports saved for {students.count()} learners.",
    )

    return redirect(
        f"/weekly-reports/staff/write/?mode=class"
        f"&class={class_value}&week={week_id}"
        f"&subject={subject_id}"
    )

