from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.staff_access import role_permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import (
    Subject,
    Teacher,
    Room,
    Period,
    Day,
    TimetableEntry,
    ExamSchedule,
    TeacherSubstitution,
    TeacherTeachingAssignment,
)


# ============================================================
# DASHBOARD
# ============================================================

@login_required
@role_permission_required("view_timetableentry", "scheduling")
def scheduling_dashboard(request):

    today = timezone.localdate()

    weekday_map = {
        0: "MONDAY",
        1: "TUESDAY",
        2: "WEDNESDAY",
        3: "THURSDAY",
        4: "FRIDAY",
        5: "SATURDAY",
        6: "SUNDAY",
    }

    today_name = weekday_map[today.weekday()]

    today_day = Day.objects.filter(name=today_name).first()

    if today_day:
        today_timetable = (
            TimetableEntry.objects
            .filter(
                day=today_day,
                is_active=True
            )
            .select_related(
                "subject",
                "teacher",
                "room",
                "period",
                "day",
            )
            .order_by(
                "period__order",
                "class_name",
                "stream",
            )
        )
    else:
        today_timetable = TimetableEntry.objects.none()

    upcoming_exams = (
        ExamSchedule.objects
        .filter(date__gte=today)
        .select_related(
            "subject",
            "room",
            "invigilator",
        )
        .order_by(
            "date",
            "start_time",
        )[:5]
    )

    recent_substitutions = (
        TeacherSubstitution.objects
        .filter(date__gte=today)
        .select_related(
            "subject",
            "absent_teacher",
            "substitute_teacher",
            "period",
            "day",
        )
        .order_by(
            "date",
            "period__order",
        )[:5]
    )

    context = {
        "page_title": "Timetable & Scheduling",
        "today": today,

        "today_name": (
            today_day.get_name_display()
            if today_day
            else today_name.title()
        ),

        "today_timetable": today_timetable,
        "upcoming_exams": upcoming_exams,
        "recent_substitutions": recent_substitutions,

        "total_subjects": Subject.objects.filter(
            is_active=True
        ).count(),

        "total_teachers": Teacher.objects.filter(
            is_active=True
        ).count(),

        "total_rooms": Room.objects.filter(
            is_active=True
        ).count(),

        "total_periods": Period.objects.filter(
            is_break=False
        ).count(),

        "total_days": Day.objects.count(),

        "total_timetable_entries": TimetableEntry.objects.filter(
            is_active=True
        ).count(),

        "total_exams": ExamSchedule.objects.filter(
            date__gte=today
        ).count(),

        "total_substitutions": TeacherSubstitution.objects.filter(
            date__gte=today
        ).count(),
    }

    return render(
        request,
        "scheduling/scheduling_dashboard.html",
        context
    )


# ============================================================
# TIMETABLE
# ============================================================

@login_required
@role_permission_required("view_timetableentry", "scheduling")
def timetable_view(request):

    days = Day.objects.all().order_by("order")

    periods = Period.objects.all().order_by("order")

    entries = (
        TimetableEntry.objects
        .filter(is_active=True)
        .select_related(
            "subject",
            "teacher",
            "room",
            "day",
            "period",
        )
    )

    class_name = request.GET.get(
        "class_name",
        ""
    ).strip()

    stream = request.GET.get(
        "stream",
        ""
    ).strip()

    teacher_id = request.GET.get(
        "teacher",
        ""
    ).strip()

    room_id = request.GET.get(
        "room",
        ""
    ).strip()

    if class_name:
        entries = entries.filter(
            class_name__iexact=class_name
        )

    if stream:
        entries = entries.filter(
            stream__iexact=stream
        )

    if teacher_id:
        entries = entries.filter(
            teacher_id=teacher_id
        )

    if room_id:
        entries = entries.filter(
            room_id=room_id
        )

    timetable_grid = {}

    for entry in entries:

        key = (
            entry.day_id,
            entry.period_id,
        )

        timetable_grid.setdefault(
            key,
            []
        ).append(entry)

    classes = (
        TimetableEntry.objects
        .filter(is_active=True)
        .values_list(
            "class_name",
            flat=True
        )
        .distinct()
        .order_by("class_name")
    )

    streams = (
        TimetableEntry.objects
        .filter(is_active=True)
        .exclude(stream__isnull=True)
        .exclude(stream="")
        .values_list(
            "stream",
            flat=True
        )
        .distinct()
        .order_by("stream")
    )

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    rooms = Room.objects.filter(
        is_active=True
    ).order_by("name")

    return render(
        request,
        "scheduling/timetable.html",
        {
            "days": days,
            "periods": periods,
            "entries": entries,
            "timetable_grid": timetable_grid,
            "classes": classes,
            "streams": streams,
            "teachers": teachers,
            "rooms": rooms,
            "selected_class": class_name,
            "selected_stream": stream,
            "selected_teacher": teacher_id,
            "selected_room": room_id,
        }
    )


# ============================================================
# ADD TIMETABLE ENTRY
# ============================================================

@login_required
@role_permission_required("add_timetableentry", "scheduling")
def add_timetable_entry(request):

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    rooms = Room.objects.filter(
        is_active=True
    ).order_by("name")

    days = Day.objects.all().order_by("order")

    periods = Period.objects.all().order_by("order")

    if request.method == "POST":

        try:

            class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            stream = request.POST.get(
                "stream",
                ""
            ).strip()

            subject_id = request.POST.get("subject")
            teacher_id = request.POST.get("teacher")
            day_id = request.POST.get("day")
            period_id = request.POST.get("period")
            room_id = request.POST.get("room")

            notes = request.POST.get(
                "notes",
                ""
            ).strip()

            if not class_name:
                raise ValueError(
                    "Class name is required."
                )

            if not subject_id:
                raise ValueError(
                    "Please select a subject."
                )

            if not day_id:
                raise ValueError(
                    "Please select a day."
                )

            if not period_id:
                raise ValueError(
                    "Please select a period."
                )

            entry = TimetableEntry(
                class_name=class_name,
                stream=stream or None,
                subject_id=subject_id,
                teacher_id=teacher_id or None,
                day_id=day_id,
                period_id=period_id,
                room_id=room_id or None,
                notes=notes or None,
            )

            entry.save()

            messages.success(
                request,
                "Timetable lesson added successfully."
            )

            return redirect(
                "scheduling:timetable"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_timetable_entry.html",
        {
            "subjects": subjects,
            "teachers": teachers,
            "rooms": rooms,
            "days": days,
            "periods": periods,
        }
    )


# ============================================================
# EDIT TIMETABLE ENTRY
# ============================================================

@login_required
@role_permission_required("change_timetableentry", "scheduling")
def edit_timetable_entry(request, entry_id):

    entry = get_object_or_404(
        TimetableEntry,
        id=entry_id
    )

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    rooms = Room.objects.filter(
        is_active=True
    ).order_by("name")

    days = Day.objects.all().order_by("order")

    periods = Period.objects.all().order_by("order")

    if request.method == "POST":

        try:

            entry.class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            entry.stream = request.POST.get(
                "stream",
                ""
            ).strip() or None

            entry.subject_id = request.POST.get(
                "subject"
            )

            entry.teacher_id = (
                request.POST.get("teacher")
                or None
            )

            entry.day_id = request.POST.get(
                "day"
            )

            entry.period_id = request.POST.get(
                "period"
            )

            entry.room_id = (
                request.POST.get("room")
                or None
            )

            entry.notes = (
                request.POST.get(
                    "notes",
                    ""
                ).strip()
                or None
            )

            if not entry.class_name:
                raise ValueError(
                    "Class name is required."
                )

            entry.save()

            messages.success(
                request,
                "Timetable lesson updated successfully."
            )

            return redirect(
                "scheduling:timetable"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_timetable_entry.html",
        {
            "entry": entry,
            "subjects": subjects,
            "teachers": teachers,
            "rooms": rooms,
            "days": days,
            "periods": periods,
        }
    )


# ============================================================
# DELETE TIMETABLE ENTRY
# ============================================================

@login_required
@role_permission_required("delete_timetableentry", "scheduling")
def delete_timetable_entry(request, entry_id):

    entry = get_object_or_404(
        TimetableEntry,
        id=entry_id
    )

    entry.is_active = False

    entry.save(
        update_fields=["is_active"]
    )

    messages.success(
        request,
        "Timetable lesson removed."
    )

    return redirect(
        "scheduling:timetable"
    )


# ============================================================
# SUBJECTS
# ============================================================

@login_required
@role_permission_required("view_subject", "scheduling")
def subject_list(request):

    subjects = Subject.objects.all().order_by("name")

    return render(
        request,
        "scheduling/subjects.html",
        {
            "subjects": subjects,
        }
    )


@login_required
@role_permission_required("add_subject", "scheduling")
def subject_add(request):

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            code = request.POST.get(
                "code",
                ""
            ).strip()

            if not name:
                raise ValueError(
                    "Subject name is required."
                )

            Subject.objects.create(
                name=name,
                code=code or None,
            )

            messages.success(
                request,
                "Subject added successfully."
            )

            return redirect(
                "scheduling:subject_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_subject.html"
    )


@login_required
@role_permission_required("change_subject", "scheduling")
def subject_edit(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id
    )

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            code = request.POST.get(
                "code",
                ""
            ).strip()

            if not name:
                raise ValueError(
                    "Subject name is required."
                )

            subject.name = name
            subject.code = code or None

            subject.save()

            messages.success(
                request,
                "Subject updated successfully."
            )

            return redirect(
                "scheduling:subject_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_subject.html",
        {
            "subject": subject,
        }
    )


@login_required
@role_permission_required("delete_subject", "scheduling")
def subject_delete(request, subject_id):

    subject = get_object_or_404(
        Subject,
        id=subject_id
    )

    subject.is_active = False

    subject.save(
        update_fields=["is_active"]
    )

    messages.success(
        request,
        "Subject removed successfully."
    )

    return redirect(
        "scheduling:subject_list"
    )


# ============================================================
# TEACHERS
# ============================================================

@login_required
@role_permission_required("view_teacher", "scheduling")
def teacher_list(request):

    teachers = Teacher.objects.all().order_by("name")

    return render(
        request,
        "scheduling/teachers.html",
        {
            "teachers": teachers,
        }
    )


@login_required
@role_permission_required("add_teacher", "scheduling")
def teacher_add(request):

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            employee_no = request.POST.get(
                "employee_no",
                ""
            ).strip()

            phone = request.POST.get(
                "phone",
                ""
            ).strip()

            email = request.POST.get(
                "email",
                ""
            ).strip()

            if not name:
                raise ValueError(
                    "Teacher name is required."
                )

            Teacher.objects.create(
                name=name,
                employee_no=employee_no or None,
                phone=phone or None,
                email=email or None,
            )

            messages.success(
                request,
                "Teacher added successfully."
            )

            return redirect(
                "scheduling:teacher_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_teacher.html"
    )


@login_required
@role_permission_required("change_teacher", "scheduling")
def teacher_edit(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    if request.method == "POST":

        try:

            teacher.name = request.POST.get(
                "name",
                ""
            ).strip()

            teacher.employee_no = (
                request.POST.get(
                    "employee_no",
                    ""
                ).strip()
                or None
            )

            teacher.phone = (
                request.POST.get(
                    "phone",
                    ""
                ).strip()
                or None
            )

            teacher.email = (
                request.POST.get(
                    "email",
                    ""
                ).strip()
                or None
            )

            if not teacher.name:
                raise ValueError(
                    "Teacher name is required."
                )

            teacher.save()

            messages.success(
                request,
                "Teacher updated successfully."
            )

            return redirect(
                "scheduling:teacher_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_teacher.html",
        {
            "teacher": teacher,
        }
    )


@login_required
@role_permission_required("delete_teacher", "scheduling")
def teacher_delete(request, teacher_id):

    teacher = get_object_or_404(
        Teacher,
        id=teacher_id
    )

    teacher.is_active = False

    teacher.save(
        update_fields=["is_active"]
    )

    messages.success(
        request,
        "Teacher removed successfully."
    )

    return redirect(
        "scheduling:teacher_list"
    )


# ============================================================
# TEACHER TEACHING ASSIGNMENTS
# ============================================================

@login_required
@role_permission_required("view_teacherteachingassignment", "scheduling")
def teacher_teaching_assignment_list(request):

    assignments = (
        TeacherTeachingAssignment.objects
        .select_related("teacher", "subject")
        .filter(is_active=True)
        .order_by(
            "teacher__name",
            "class_name",
            "stream",
            "subject__name"
        )
    )


    total_weekly_lessons = sum(
        assignment.lessons_per_week
        for assignment in assignments
    )

    return render(
        request,
        "scheduling/teacher_teaching_assignments.html",
        {
            "assignments": assignments,
            "total_weekly_lessons": total_weekly_lessons,
        }
    )


@login_required
@role_permission_required("add_teacherteachingassignment", "scheduling")
def teacher_teaching_assignment_add(request):

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            teacher_id = request.POST.get("teacher", "").strip()
            subject_id = request.POST.get("subject", "").strip()
            class_name = request.POST.get("class_name", "").strip()
            stream = request.POST.get("stream", "").strip()
            lessons_per_week = request.POST.get(
                "lessons_per_week",
                "1"
            ).strip()

            is_active = request.POST.get("is_active") == "on"

            if not teacher_id:
                raise ValueError("Teacher is required.")

            if not subject_id:
                raise ValueError("Subject is required.")

            if not class_name:
                raise ValueError("Class name is required.")

            try:
                lessons_per_week = int(lessons_per_week)
            except ValueError:
                raise ValueError(
                    "Lessons per week must be a whole number."
                )

            if lessons_per_week < 1:
                raise ValueError(
                    "Lessons per week must be at least 1."
                )

            teacher = get_object_or_404(
                Teacher,
                id=teacher_id,
                is_active=True
            )

            subject = get_object_or_404(
                Subject,
                id=subject_id,
                is_active=True
            )

            duplicate = TeacherTeachingAssignment.objects.filter(
                teacher=teacher,
                subject=subject,
                class_name=class_name,
                stream=stream or None,
            ).exists()

            if duplicate:
                raise ValueError(
                    "This teacher, subject, class and stream assignment "
                    "already exists."
                )

            TeacherTeachingAssignment.objects.create(
                teacher=teacher,
                subject=subject,
                class_name=class_name,
                stream=stream or None,
                lessons_per_week=lessons_per_week,
                is_active=is_active,
            )

            messages.success(
                request,
                "Teaching assignment added successfully."
            )

            return redirect(
                "scheduling:teacher_teaching_assignment_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/teacher_teaching_assignment_form.html",
        {
            "teachers": teachers,
            "subjects": subjects,
            "assignment": None,
        }
    )


@login_required
@role_permission_required("change_teacherteachingassignment", "scheduling")
def teacher_teaching_assignment_edit(request, assignment_id):

    assignment = get_object_or_404(
        TeacherTeachingAssignment,
        id=assignment_id
    )

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            teacher_id = request.POST.get("teacher", "").strip()
            subject_id = request.POST.get("subject", "").strip()
            class_name = request.POST.get("class_name", "").strip()
            stream = request.POST.get("stream", "").strip()
            lessons_per_week = request.POST.get(
                "lessons_per_week",
                "1"
            ).strip()

            is_active = request.POST.get("is_active") == "on"

            if not teacher_id:
                raise ValueError("Teacher is required.")

            if not subject_id:
                raise ValueError("Subject is required.")

            if not class_name:
                raise ValueError("Class name is required.")

            try:
                lessons_per_week = int(lessons_per_week)
            except ValueError:
                raise ValueError(
                    "Lessons per week must be a whole number."
                )

            if lessons_per_week < 1:
                raise ValueError(
                    "Lessons per week must be at least 1."
                )

            teacher = get_object_or_404(
                Teacher,
                id=teacher_id,
                is_active=True
            )

            subject = get_object_or_404(
                Subject,
                id=subject_id,
                is_active=True
            )

            duplicate = TeacherTeachingAssignment.objects.filter(
                teacher=teacher,
                subject=subject,
                class_name=class_name,
                stream=stream or None,
            ).exclude(
                id=assignment.id
            ).exists()

            if duplicate:
                raise ValueError(
                    "Another identical teaching assignment already exists."
                )

            assignment.teacher = teacher
            assignment.subject = subject
            assignment.class_name = class_name
            assignment.stream = stream or None
            assignment.lessons_per_week = lessons_per_week
            assignment.is_active = is_active

            assignment.save()

            messages.success(
                request,
                "Teaching assignment updated successfully."
            )

            return redirect(
                "scheduling:teacher_teaching_assignment_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/teacher_teaching_assignment_form.html",
        {
            "teachers": teachers,
            "subjects": subjects,
            "assignment": assignment,
        }
    )


@login_required
@role_permission_required("delete_teacherteachingassignment", "scheduling")
def teacher_teaching_assignment_delete(request, assignment_id):

    assignment = get_object_or_404(
        TeacherTeachingAssignment,
        id=assignment_id
    )

    assignment.is_active = False

    assignment.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Teaching assignment deactivated successfully."
    )

    return redirect(
        "scheduling:teacher_teaching_assignment_list"
    )


# ============================================================
# ROOMS
# ============================================================

@login_required
@role_permission_required("view_room", "scheduling")
def room_list(request):

    rooms = Room.objects.all().order_by("name")

    return render(
        request,
        "scheduling/rooms.html",
        {
            "rooms": rooms,
        }
    )


@login_required
@role_permission_required("add_room", "scheduling")
def room_add(request):

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            capacity = request.POST.get(
                "capacity",
                ""
            ).strip()

            room_type = request.POST.get(
                "room_type",
                ""
            ).strip()

            if not name:
                raise ValueError(
                    "Room name is required."
                )

            if capacity:
                capacity_value = int(capacity)

                if capacity_value < 0:
                    raise ValueError(
                        "Room capacity cannot be negative."
                    )
            else:
                capacity_value = None

            Room.objects.create(
                name=name,
                capacity=capacity_value,
                room_type=room_type or None,
            )

            messages.success(
                request,
                "Room added successfully."
            )

            return redirect(
                "scheduling:room_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_room.html"
    )


@login_required
@role_permission_required("change_room", "scheduling")
def room_edit(request, room_id):

    room = get_object_or_404(
        Room,
        id=room_id
    )

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            capacity = request.POST.get(
                "capacity",
                ""
            ).strip()

            room_type = request.POST.get(
                "room_type",
                ""
            ).strip()

            if not name:
                raise ValueError(
                    "Room name is required."
                )

            if capacity:
                capacity_value = int(capacity)

                if capacity_value < 0:
                    raise ValueError(
                        "Room capacity cannot be negative."
                    )
            else:
                capacity_value = None

            room.name = name
            room.capacity = capacity_value
            room.room_type = room_type or None

            room.save()

            messages.success(
                request,
                "Room updated successfully."
            )

            return redirect(
                "scheduling:room_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_room.html",
        {
            "room": room,
        }
    )


@login_required
@role_permission_required("delete_room", "scheduling")
def room_delete(request, room_id):

    room = get_object_or_404(
        Room,
        id=room_id
    )

    room.is_active = False

    room.save(
        update_fields=["is_active"]
    )

    messages.success(
        request,
        "Room removed successfully."
    )

    return redirect(
        "scheduling:room_list"
    )


# ============================================================
# PERIODS
# ============================================================

@login_required
@role_permission_required("view_period", "scheduling")
def period_list(request):

    periods = Period.objects.all().order_by("order")

    return render(
        request,
        "scheduling/periods.html",
        {
            "periods": periods,
        }
    )


@login_required
@role_permission_required("add_period", "scheduling")
def period_add(request):

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name",
                ""
            ).strip()

            start_time = request.POST.get(
                "start_time"
            )

            end_time = request.POST.get(
                "end_time"
            )

            order = request.POST.get(
                "order",
                "1"
            )

            is_break = (
                request.POST.get("is_break")
                == "on"
            )

            if not name:
                raise ValueError(
                    "Period name is required."
                )

            if not start_time or not end_time:
                raise ValueError(
                    "Start time and end time are required."
                )

            Period.objects.create(
                name=name,
                start_time=start_time,
                end_time=end_time,
                order=int(order),
                is_break=is_break,
            )

            messages.success(
                request,
                "Period added successfully."
            )

            return redirect(
                "scheduling:period_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_period.html"
    )


@login_required
@role_permission_required("change_period", "scheduling")
def period_edit(request, period_id):

    period = get_object_or_404(
        Period,
        id=period_id
    )

    if request.method == "POST":

        try:

            period.name = request.POST.get(
                "name",
                ""
            ).strip()

            period.start_time = request.POST.get(
                "start_time"
            )

            period.end_time = request.POST.get(
                "end_time"
            )

            period.order = int(
                request.POST.get(
                    "order",
                    "1"
                )
            )

            period.is_break = (
                request.POST.get("is_break")
                == "on"
            )

            if not period.name:
                raise ValueError(
                    "Period name is required."
                )

            period.save()

            messages.success(
                request,
                "Period updated successfully."
            )

            return redirect(
                "scheduling:period_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_period.html",
        {
            "period": period,
        }
    )


@login_required
@role_permission_required("delete_period", "scheduling")
def period_delete(request, period_id):

    period = get_object_or_404(
        Period,
        id=period_id
    )

    period.delete()

    messages.success(
        request,
        "Period deleted successfully."
    )

    return redirect(
        "scheduling:period_list"
    )


# ============================================================
# DAYS
# ============================================================

@login_required
@role_permission_required("view_day", "scheduling")
def day_list(request):

    days = Day.objects.all().order_by("order")

    return render(
        request,
        "scheduling/days.html",
        {
            "days": days,
        }
    )


@login_required
@role_permission_required("add_day", "scheduling")
def day_add(request):

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name"
            )

            order = request.POST.get(
                "order",
                "1"
            )

            if not name:
                raise ValueError(
                    "Please select a day."
                )

            Day.objects.create(
                name=name,
                order=int(order),
            )

            messages.success(
                request,
                "Day added successfully."
            )

            return redirect(
                "scheduling:day_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_day.html",
        {
            "day_choices": Day.DAY_CHOICES,
        }
    )


@login_required
@role_permission_required("change_day", "scheduling")
def day_edit(request, day_id):

    day = get_object_or_404(
        Day,
        id=day_id
    )

    if request.method == "POST":

        try:

            name = request.POST.get(
                "name"
            )

            order = request.POST.get(
                "order",
                "1"
            )

            if not name:
                raise ValueError(
                    "Please select a day."
                )

            day.name = name
            day.order = int(order)

            day.save()

            messages.success(
                request,
                "Day updated successfully."
            )

            return redirect(
                "scheduling:day_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_day.html",
        {
            "day": day,
            "day_choices": Day.DAY_CHOICES,
        }
    )


@login_required
@role_permission_required("delete_day", "scheduling")
def day_delete(request, day_id):

    day = get_object_or_404(
        Day,
        id=day_id
    )

    day.delete()

    messages.success(
        request,
        "Day deleted successfully."
    )

    return redirect(
        "scheduling:day_list"
    )


# ============================================================
# EXAMS
# ============================================================

@login_required
@role_permission_required("view_examschedule", "scheduling")
def exam_list(request):

    exams = (
        ExamSchedule.objects
        .select_related(
            "subject",
            "room",
            "invigilator",
        )
        .order_by(
            "date",
            "start_time"
        )
    )

    return render(
        request,
        "scheduling/exams.html",
        {
            "exams": exams,
        }
    )


@login_required
@role_permission_required("add_examschedule", "scheduling")
def exam_add(request):

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    rooms = Room.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            exam_name = request.POST.get(
                "exam_name",
                ""
            ).strip()

            class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            subject_id = request.POST.get(
                "subject"
            )

            date = request.POST.get(
                "date"
            )

            start_time = request.POST.get(
                "start_time"
            )

            end_time = request.POST.get(
                "end_time"
            )

            if not exam_name:
                raise ValueError(
                    "Exam name is required."
                )

            if not class_name:
                raise ValueError(
                    "Class name is required."
                )

            if not subject_id:
                raise ValueError(
                    "Please select a subject."
                )

            if not date:
                raise ValueError(
                    "Exam date is required."
                )

            if not start_time or not end_time:
                raise ValueError(
                    "Start time and end time are required."
                )

            ExamSchedule.objects.create(
                exam_name=exam_name,
                exam_type=request.POST.get(
                    "exam_type",
                    "OTHER"
                ),
                class_name=class_name,
                stream=request.POST.get(
                    "stream",
                    ""
                ).strip() or None,
                subject_id=subject_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                room_id=request.POST.get(
                    "room"
                ) or None,
                invigilator_id=request.POST.get(
                    "invigilator"
                ) or None,
                instructions=request.POST.get(
                    "instructions",
                    ""
                ).strip() or None,
            )

            messages.success(
                request,
                "Exam schedule added successfully."
            )

            return redirect(
                "scheduling:exam_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_exam.html",
        {
            "subjects": subjects,
            "rooms": rooms,
            "teachers": teachers,
            "exam_types": ExamSchedule.EXAM_TYPE_CHOICES,
        }
    )


@login_required
@role_permission_required("change_examschedule", "scheduling")
def exam_edit(request, exam_id):

    exam = get_object_or_404(
        ExamSchedule,
        id=exam_id
    )

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    rooms = Room.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            exam.exam_name = request.POST.get(
                "exam_name",
                ""
            ).strip()

            exam.exam_type = request.POST.get(
                "exam_type",
                "OTHER"
            )

            exam.class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            exam.stream = (
                request.POST.get(
                    "stream",
                    ""
                ).strip()
                or None
            )

            exam.subject_id = request.POST.get(
                "subject"
            )

            exam.date = request.POST.get(
                "date"
            )

            exam.start_time = request.POST.get(
                "start_time"
            )

            exam.end_time = request.POST.get(
                "end_time"
            )

            exam.room_id = (
                request.POST.get(
                    "room"
                )
                or None
            )

            exam.invigilator_id = (
                request.POST.get(
                    "invigilator"
                )
                or None
            )

            exam.instructions = (
                request.POST.get(
                    "instructions",
                    ""
                ).strip()
                or None
            )

            if not exam.exam_name:
                raise ValueError(
                    "Exam name is required."
                )

            if not exam.class_name:
                raise ValueError(
                    "Class name is required."
                )

            exam.save()

            messages.success(
                request,
                "Exam schedule updated successfully."
            )

            return redirect(
                "scheduling:exam_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_exam.html",
        {
            "exam": exam,
            "subjects": subjects,
            "rooms": rooms,
            "teachers": teachers,
            "exam_types": ExamSchedule.EXAM_TYPE_CHOICES,
        }
    )


@login_required
@role_permission_required("delete_examschedule", "scheduling")
def exam_delete(request, exam_id):

    exam = get_object_or_404(
        ExamSchedule,
        id=exam_id
    )

    exam.delete()

    messages.success(
        request,
        "Exam deleted successfully."
    )

    return redirect(
        "scheduling:exam_list"
    )


# ============================================================
# TEACHER SUBSTITUTIONS
# ============================================================

@login_required
@role_permission_required("view_teachersubstitution", "scheduling")
def substitution_list(request):

    substitutions = (
        TeacherSubstitution.objects
        .select_related(
            "day",
            "period",
            "subject",
            "absent_teacher",
            "substitute_teacher",
        )
        .order_by(
            "-date",
            "period__order"
        )
    )

    return render(
        request,
        "scheduling/substitutions.html",
        {
            "substitutions": substitutions,
        }
    )


@login_required
@role_permission_required("add_teachersubstitution", "scheduling")
def substitution_add(request):

    days = Day.objects.all().order_by("order")

    periods = Period.objects.all().order_by("order")

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            date = request.POST.get("date")
            day_id = request.POST.get("day")
            period_id = request.POST.get("period")
            class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            subject_id = request.POST.get(
                "subject"
            )

            absent_teacher_id = request.POST.get(
                "absent_teacher"
            )

            substitute_teacher_id = request.POST.get(
                "substitute_teacher"
            )

            if not date:
                raise ValueError(
                    "Date is required."
                )

            if not day_id:
                raise ValueError(
                    "Please select a day."
                )

            if not period_id:
                raise ValueError(
                    "Please select a period."
                )

            if not class_name:
                raise ValueError(
                    "Class name is required."
                )

            if not subject_id:
                raise ValueError(
                    "Please select a subject."
                )

            if not absent_teacher_id:
                raise ValueError(
                    "Please select the absent teacher."
                )

            if not substitute_teacher_id:
                raise ValueError(
                    "Please select the substitute teacher."
                )

            TeacherSubstitution.objects.create(
                date=date,
                day_id=day_id,
                period_id=period_id,
                class_name=class_name,
                stream=request.POST.get(
                    "stream",
                    ""
                ).strip() or None,
                subject_id=subject_id,
                absent_teacher_id=absent_teacher_id,
                substitute_teacher_id=substitute_teacher_id,
                reason=request.POST.get(
                    "reason",
                    ""
                ).strip() or None,
                notes=request.POST.get(
                    "notes",
                    ""
                ).strip() or None,
            )

            messages.success(
                request,
                "Teacher substitution added successfully."
            )

            return redirect(
                "scheduling:substitution_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/add_substitution.html",
        {
            "days": days,
            "periods": periods,
            "subjects": subjects,
            "teachers": teachers,
        }
    )


@login_required
@role_permission_required("change_teachersubstitution", "scheduling")
def substitution_edit(
    request,
    substitution_id
):

    substitution = get_object_or_404(
        TeacherSubstitution,
        id=substitution_id
    )

    days = Day.objects.all().order_by("order")

    periods = Period.objects.all().order_by("order")

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        try:

            substitution.date = request.POST.get(
                "date"
            )

            substitution.day_id = request.POST.get(
                "day"
            )

            substitution.period_id = request.POST.get(
                "period"
            )

            substitution.class_name = request.POST.get(
                "class_name",
                ""
            ).strip()

            substitution.stream = (
                request.POST.get(
                    "stream",
                    ""
                ).strip()
                or None
            )

            substitution.subject_id = request.POST.get(
                "subject"
            )

            substitution.absent_teacher_id = request.POST.get(
                "absent_teacher"
            )

            substitution.substitute_teacher_id = request.POST.get(
                "substitute_teacher"
            )

            substitution.reason = (
                request.POST.get(
                    "reason",
                    ""
                ).strip()
                or None
            )

            substitution.notes = (
                request.POST.get(
                    "notes",
                    ""
                ).strip()
                or None
            )

            if not substitution.class_name:
                raise ValueError(
                    "Class name is required."
                )

            substitution.save()

            messages.success(
                request,
                "Teacher substitution updated successfully."
            )

            return redirect(
                "scheduling:substitution_list"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "scheduling/edit_substitution.html",
        {
            "substitution": substitution,
            "days": days,
            "periods": periods,
            "subjects": subjects,
            "teachers": teachers,
        }
    )


@login_required
@role_permission_required("delete_teachersubstitution", "scheduling")
def substitution_delete(
    request,
    substitution_id
):

    substitution = get_object_or_404(
        TeacherSubstitution,
        id=substitution_id
    )

    substitution.delete()

    messages.success(
        request,
        "Teacher substitution deleted successfully."
    )

    return redirect(
        "scheduling:substitution_list"
    )

# ============================================================
# AUTOMATIC TIMETABLE GENERATOR
# ============================================================

@login_required
@role_permission_required("add_timetableentry", "scheduling")
def timetable_generator(request):
    result = None

    if request.method == "POST":
        from scheduling.generator import generate_timetable

        clear_draft = request.POST.get("clear_draft") == "on"

        try:
            result = generate_timetable(
                clear_existing_draft=clear_draft
            )

            scheduled = result.get("scheduled", 0)
            required = result.get("total_required", 0)
            unscheduled = result.get("unscheduled", [])

            if unscheduled:
                messages.warning(
                    request,
                    f"Timetable generated with {scheduled} of "
                    f"{required} required lessons scheduled."
                )

            if not unscheduled:
                messages.success(
                    request,
                    f"Timetable draft generated successfully. "
                    f"{scheduled} of {required} lessons scheduled."
                )

        except Exception as exc:
            messages.error(
                request,
                f"Timetable generation failed: {exc}"
            )

    return render(
        request,
        "scheduling/timetable_generator.html",
        {
            "result": result,
        },
    )

# ============================================================
# TIMETABLE REVIEW
# ============================================================

@login_required
@role_permission_required("view_timetableentry", "scheduling")
def timetable_review(request):

    entries = (
        TimetableEntry.objects
        .select_related(
            "subject",
            "teacher",
            "day",
            "period",
            "room",
        )
        .filter(is_active=True)
        .order_by(
            "day__order",
            "period__order",
            "class_name",
            "stream",
        )
    )

    return render(
        request,
        "scheduling/timetable_review.html",
        {
            "entries": entries,
        },
    )


# ============================================================
# TIMETABLE PUBLICATION WORKFLOW
# ============================================================

@login_required
@role_permission_required("change_timetableentry", "scheduling")
def publish_timetable(request):
    """
    Publish the current generated timetable.

    Only active, non-fixed draft entries are published.
    Existing published entries are first cleared so the
    resulting timetable represents one coherent publication.
    """
    from django.contrib import messages
    from django.shortcuts import redirect, render
    from .models import TimetableEntry

    if request.method != "POST":
        return render(
            request,
            "scheduling/timetable_publish_confirm.html",
            {
                "draft_count": TimetableEntry.objects.filter(
                    is_active=True,
                    is_published=False,
                    notes="Automatically generated draft",
                ).count(),
                "published_count": TimetableEntry.objects.filter(
                    is_active=True,
                    is_published=True,
                ).count(),
            },
        )

    with transaction.atomic():
        draft_entries = TimetableEntry.objects.filter(
            is_active=True,
            is_published=False,
            notes="Automatically generated draft",
        )

        draft_count = draft_entries.count()

        TimetableEntry.objects.filter(
            is_active=True,
            is_published=True,
        ).update(is_published=False)

        draft_entries.update(is_published=True)

    messages.success(
        request,
        f"Timetable published successfully. {draft_count} lessons are now visible to portal users."
    )

    return redirect("scheduling:timetable_review")


@login_required
@role_permission_required("change_timetableentry", "scheduling")
def unpublish_timetable(request):
    """
    Remove timetable visibility from portal users without deleting entries.
    """
    from django.contrib import messages
    from django.shortcuts import redirect, render
    from .models import TimetableEntry

    if request.method != "POST":
        published_count = TimetableEntry.objects.filter(
            is_active=True,
            is_published=True,
        ).count()

        return render(
            request,
            "scheduling/timetable_unpublish_confirm.html",
            {
                "published_count": published_count,
            },
        )

    with transaction.atomic():
        updated = TimetableEntry.objects.filter(
            is_active=True,
            is_published=True,
        ).update(is_published=False)

    messages.success(
        request,
        f"Timetable unpublished successfully. {updated} lessons were returned to draft visibility."
    )

    return redirect("scheduling:timetable_review")


@login_required
def published_timetable_view(request):
    """
    Portal-safe timetable view.
    Only published active entries are displayed.
    """
    from django.shortcuts import render
    from .models import TimetableEntry, Day, Period

    entries = (
        TimetableEntry.objects
        .filter(
            is_active=True,
            is_published=True,
        )
        .select_related(
            "subject",
            "teacher",
            "room",
            "day",
            "period",
        )
        .order_by(
            "day__order",
            "period__order",
            "class_name",
        )
    )

    return render(
        request,
        "scheduling/published_timetable.html",
        {
            "entries": entries,
            "days": Day.objects.all().order_by("order"),
            "periods": Period.objects.filter(
                is_break=False
            ).order_by("order"),
        },
    )


# ============================================================
# COMPLETE TIMETABLE MANAGEMENT CENTRE
# ============================================================

@login_required
@role_permission_required("view_timetableentry", "scheduling")

# ============================================================
# TIMETABLE MANAGEMENT CENTRE
# ============================================================

def timetable_management_centre(request):
    from django.shortcuts import render
    from scheduling.models import (
        Teacher,
        Subject,
        TeacherClassAssignment,
        TeacherTeachingAssignment,
    )
    from academic.models import Stream
    from students.models import Student

    teachers = (
        Teacher.objects
        .filter(is_active=True)
        .order_by("name")
    )

    subjects = (
        Subject.objects
        .filter(is_active=True)
        .order_by("name")
    )

    streams = (
        Stream.objects
        .filter(is_active=True)
        .order_by("name")
    )

    class_names = set()

    class_assignment_values = (
        TeacherClassAssignment.objects
        .filter(is_active=True)
        .values_list("class_name", flat=True)
    )

    for value in class_assignment_values:
        value = (value or "").strip()
        if value:
            class_names.add(value)

    teaching_assignment_values = (
        TeacherTeachingAssignment.objects
        .filter(is_active=True)
        .values_list("class_name", flat=True)
    )

    for value in teaching_assignment_values:
        value = (value or "").strip()
        if value:
            class_names.add(value)

    student_class_values = (
        Student.objects
        .values_list("class_name", flat=True)
    )

    for value in student_class_values:
        value = (value or "").strip()
        if value:
            class_names.add(value)

    try:
        from lms.models import CourseClass

        course_class_values = (
            CourseClass.objects
            .filter(is_active=True)
            .values_list("class_name", flat=True)
        )

        for value in course_class_values:
            value = (value or "").strip()
            if value:
                class_names.add(value)

    except Exception:
        pass

    classes = sorted(
        class_names,
        key=lambda value: (
            value.upper(),
            value,
        ),
    )

    return render(
        request,
        "scheduling/timetable_management_centre.html",
        {
            "teachers": teachers,
            "subjects": subjects,
            "streams": streams,
            "classes": classes,
        },
    )


@login_required
@role_permission_required("view_timetableentry", "scheduling")
def timetable_create_select(request):
    from django.shortcuts import render
    from fees.models import AcademicYear, Term

    academic_years = (
        AcademicYear.objects
        .filter(is_active=True)
        .order_by("-year")
    )

    terms = (
        Term.objects
        .filter(is_active=True)
        .order_by("order", "name")
    )

    return render(
        request,
        "scheduling/timetable_create_select.html",
        {
            "academic_years": academic_years,
            "terms": terms,
        },
    )

@login_required
@role_permission_required("view_timetableentry", "scheduling")
def complete_timetable_centre(request):

    from django.contrib import messages
    from django.shortcuts import render, redirect
    from .models import (
        Day,
        Period,
        Room,
        Subject,
        Teacher,
        TeacherTeachingAssignment,
        TimetableAssignmentGroup,
        TimetableAssignmentMember,
        TimetableSlotRule,
        TimetableVersion,
    )

    from .complete_timetable_system import (
        check_timetable,
        current_draft,
        published_version,
        generate_draft,
        publish_draft,
        unpublish,
    )

    if request.method == "POST":

        action = (
            request.POST.get("action", "")
            or ""
        ).strip()

        if action == "generate":

            if not user_has_role_permission(
                request.user,
                "add_timetableentry",
                "scheduling",
            ):
                messages.error(
                    request,
                    "You do not have permission to generate a timetable.",
                )
                return redirect(
                    "scheduling:complete_timetable_centre"
                )

            result = generate_draft(
                clear_existing_draft=True
            )

            if result["unscheduled"]:

                messages.warning(
                    request,
                    (
                        f"Draft generated with "
                        f"{len(result['unscheduled'])} "
                        f"unscheduled lesson(s). "
                        "Fix the assignments before publishing."
                    )
                )

            if not result["unscheduled"]:

                messages.success(
                    request,
                    (
                        "New timetable draft generated "
                        "successfully. It has not been published."
                    )
                )

            return redirect(
                "scheduling:complete_timetable_centre"
            )

        if action == "publish":

            if not user_has_role_permission(
                request.user,
                "change_timetableentry",
                "scheduling",
            ):
                messages.error(
                    request,
                    "You do not have permission to publish a timetable.",
                )
                return redirect(
                    "scheduling:complete_timetable_centre"
                )

            try:

                version = publish_draft()

                messages.success(
                    request,
                    (
                        f"Timetable version {version.id} "
                        "has been published successfully."
                    )
                )

            except Exception as exc:

                messages.error(
                    request,
                    str(exc)
                )

            return redirect(
                "scheduling:complete_timetable_centre"
            )

        if action == "unpublish":

            if not user_has_role_permission(
                request.user,
                "change_timetableentry",
                "scheduling",
            ):
                messages.error(
                    request,
                    "You do not have permission to unpublish a timetable.",
                )
                return redirect(
                    "scheduling:complete_timetable_centre"
                )

            count = unpublish()

            messages.success(
                request,
                (
                    f"{count} timetable entries "
                    "were unpublished."
                )
            )

            return redirect(
                "scheduling:complete_timetable_centre"
            )

    draft = current_draft()
    published = published_version()

    validation = check_timetable(
        draft
    )

    assignments = (
        TeacherTeachingAssignment.objects
        .filter(is_active=True)
        .select_related(
            "teacher",
            "subject",
        )
        .order_by(
            "class_name",
            "stream",
            "subject__name",
        )
    )

    groups = (
        TimetableAssignmentGroup.objects
        .filter(is_active=True)
        .prefetch_related(
            "members__teacher",
            "members__subject",
        )
        .order_by(
            "class_name",
            "stream",
            "-created_at",
        )
    )

    versions = (
        TimetableVersion.objects
        .order_by(
            "-created_at",
            "-id",
        )[:30]
    )

    context = {
        "days": Day.objects.all().order_by("order"),
        "periods": Period.objects.all().order_by("order"),
        "rooms": Room.objects.filter(
            is_active=True
        ).order_by("name"),
        "subjects": Subject.objects.filter(
            is_active=True
        ).order_by("name"),
        "teachers": Teacher.objects.filter(
            is_active=True
        ).order_by("name"),
        "slot_rules": TimetableSlotRule.objects.all().select_related(
            "day",
            "period",
        ),
        "assignments": assignments,
        "assignment_groups": groups,
        "versions": versions,
        "draft": draft,
        "published": published,
        "validation": validation,
    }

    return render(
        request,
        "scheduling/complete_timetable_centre.html",
        context,
    )


@login_required
@role_permission_required(
    "add_teacherteachingassignment",
    "scheduling",
)
def timetable_assignment_add(request):

    from django.contrib import messages
    from django.shortcuts import render, redirect
    from .models import (
        Subject,
        Teacher,
        TeacherTeachingAssignment,
    )

    teachers = Teacher.objects.filter(
        is_active=True
    ).order_by("name")

    subjects = Subject.objects.filter(
        is_active=True
    ).order_by("name")

    if request.method == "POST":

        teacher_id = request.POST.get(
            "teacher"
        )

        subject_id = request.POST.get(
            "subject"
        )

        class_name = (
            request.POST.get(
                "class_name",
                "",
            )
            or ""
        ).strip()

        stream = (
            request.POST.get(
                "stream",
                "",
            )
            or ""
        ).strip()

        lessons = request.POST.get(
            "lessons_per_week",
            "1",
        )

        duration = (
            request.POST.get(
                "duration",
                "SINGLE",
            )
            or "SINGLE"
        )

        errors = []

        if not teacher_id:
            errors.append(
                "Teacher is required."
            )

        if not subject_id:
            errors.append(
                "Subject is required."
            )

        if not class_name:
            errors.append(
                "Grade/Class is required."
            )

        try:
            lessons = int(lessons)
        except Exception:
            lessons = 0

        if lessons <= 0:
            errors.append(
                "Lessons per week must be greater than zero."
            )

        teacher = None
        subject = None

        if teacher_id:
            teacher = teachers.filter(
                id=teacher_id
            ).first()

            if teacher is None:
                errors.append(
                    "Selected teacher is invalid."
                )

        if subject_id:
            subject = subjects.filter(
                id=subject_id
            ).first()

            if subject is None:
                errors.append(
                    "Selected subject is invalid."
                )

        if not errors:

            assignment = (
                TeacherTeachingAssignment.objects
                .filter(
                    teacher=teacher,
                    subject=subject,
                    class_name=class_name,
                    stream=stream or None,
                )
                .first()
            )

            if assignment:

                assignment.lessons_per_week = lessons
                assignment.is_active = True
                assignment.save(
                    update_fields=[
                        "lessons_per_week",
                        "is_active",
                    ]
                )

                messages.success(
                    request,
                    "Existing teaching assignment updated."
                )

            if not assignment:

                TeacherTeachingAssignment.objects.create(
                    teacher=teacher,
                    subject=subject,
                    class_name=class_name,
                    stream=stream or None,
                    lessons_per_week=lessons,
                    is_active=True,
                )

                messages.success(
                    request,
                    "Teaching assignment added successfully."
                )

            return redirect(
                "scheduling:complete_timetable_centre"
            )

        for error in errors:
            messages.error(
                request,
                error
            )

    return render(
        request,
        "scheduling/timetable_assignment_form.html",
        {
            "teachers": teachers,
            "subjects": subjects,
        }
    )


@login_required
@role_permission_required(
    "delete_teacherteachingassignment",
    "scheduling",
)
def timetable_assignment_delete(
    request,
    pk,
):

    from django.contrib import messages
    from django.shortcuts import redirect
    from .models import TeacherTeachingAssignment

    if request.method == "POST":

        assignment = (
            TeacherTeachingAssignment.objects
            .filter(pk=pk)
            .first()
        )

        if assignment:

            assignment.is_active = False

            assignment.save(
                update_fields=[
                    "is_active"
                ]
            )

            messages.success(
                request,
                "Teaching assignment removed."
            )

        return redirect(
            "scheduling:complete_timetable_centre"
        )

    return redirect(
        "scheduling:complete_timetable_centre"
    )


@login_required
@role_permission_required(
    "change_timetableslotrule",
    "scheduling",
)
def timetable_slot_rule_save(request):

    from django.contrib import messages
    from django.shortcuts import redirect
    from .models import (
        Day,
        Period,
        TimetableSlotRule,
    )

    if request.method != "POST":
        return redirect(
            "scheduling:complete_timetable_centre"
        )

    day_id = request.POST.get("day")
    period_id = request.POST.get("period")
    slot_type = (
        request.POST.get(
            "slot_type",
            "LESSON",
        )
        or "LESSON"
    )

    valid_types = {
        TimetableSlotRule.TYPE_LESSON,
        TimetableSlotRule.TYPE_BREAK,
        TimetableSlotRule.TYPE_LUNCH,
        TimetableSlotRule.TYPE_GAMES,
        TimetableSlotRule.TYPE_ACTIVITY,
    }

    if slot_type not in valid_types:

        messages.error(
            request,
            "Invalid timetable slot type."
        )

        return redirect(
            "scheduling:complete_timetable_centre"
        )

    day = Day.objects.filter(
        id=day_id
    ).first()

    period = Period.objects.filter(
        id=period_id
    ).first()

    if day is None or period is None:

        messages.error(
            request,
            "Invalid day or period."
        )

        return redirect(
            "scheduling:complete_timetable_centre"
        )

    TimetableSlotRule.objects.update_or_create(
        day=day,
        period=period,
        defaults={
            "slot_type": slot_type,
            "is_enabled": True,
            "notes": (
                request.POST.get(
                    "notes",
                    "",
                )
                or ""
            ).strip(),
        }
    )

    messages.success(
        request,
        (
            f"{day} {period} configured as "
            f"{slot_type}."
        )
    )

    return redirect(
        "scheduling:complete_timetable_centre"
    )


@login_required
@role_permission_required(
    "view_timetableentry",
    "scheduling",
)
def timetable_check_view(request):

    from django.shortcuts import render
    from .complete_timetable_system import (
        check_timetable,
        current_draft,
    )

    draft = current_draft()

    result = check_timetable(
        draft
    )

    return render(
        request,
        "scheduling/timetable_check.html",
        {
            "draft": draft,
            "result": result,
        }
    )


@login_required
@role_permission_required(
    "view_timetableentry",
    "scheduling",
)
def timetable_print_class(request):

    from django.shortcuts import render
    from .models import Day, Period
    from .complete_timetable_system import (
        class_entries,
        published_version,
    )

    class_name = (
        request.GET.get(
            "class_name",
            "",
        )
        or ""
    ).strip()

    stream = (
        request.GET.get(
            "stream",
            "",
        )
        or ""
    ).strip()

    entries = class_entries(
        class_name,
        stream,
    )

    return render(
        request,
        "scheduling/timetable_print.html",
        {
            "title": "Class Timetable",
            "class_name": class_name,
            "stream": stream,
            "teacher_name": "",
            "entries": entries,
            "days": Day.objects.all().order_by("order"),
            "periods": Period.objects.all().order_by("order"),
            "published": published_version(),
            "auto_print": request.GET.get("print") == "1",
        }
    )


@login_required
@role_permission_required(
    "view_timetableentry",
    "scheduling",
)
def timetable_print_teacher(request):

    from django.shortcuts import render
    from .models import Day, Period, Teacher
    from .complete_timetable_system import (
        teacher_entries,
        published_version,
    )

    teacher_id = request.GET.get(
        "teacher"
    )

    teacher = (
        Teacher.objects
        .filter(
            id=teacher_id,
            is_active=True,
        )
        .first()
    )

    entries = teacher_entries(
        teacher
    )

    return render(
        request,
        "scheduling/timetable_print.html",
        {
            "title": "Teacher Timetable",
            "class_name": "",
            "stream": "",
            "teacher_name": (
                teacher.name
                if teacher
                else ""
            ),
            "entries": entries,
            "days": Day.objects.all().order_by("order"),
            "periods": Period.objects.all().order_by("order"),
            "published": published_version(),
            "auto_print": request.GET.get("print") == "1",
        }
    )


@login_required
@role_permission_required(
    "view_timetableentry",
    "scheduling",
)
def timetable_print_school(request):

    from django.shortcuts import render
    from .models import Day, Period
    from .complete_timetable_system import (
        published_entries,
        published_version,
    )

    entries = published_entries()

    return render(
        request,
        "scheduling/timetable_print.html",
        {
            "title": "Whole School Timetable",
            "class_name": "",
            "stream": "",
            "teacher_name": "",
            "entries": entries,
            "days": Day.objects.all().order_by("order"),
            "periods": Period.objects.all().order_by("order"),
            "published": published_version(),
            "auto_print": request.GET.get("print") == "1",
        }
    )


@login_required
def teacher_published_timetable(request):

    from django.shortcuts import render
    from .complete_timetable_system import (
        teacher_entries,
    )

    teacher = None

    try:

        profile = request.user.profile

        if profile.employee_id:
            teacher = getattr(
                profile.employee,
                "scheduling_teacher",
                None,
            )

    except Exception:
        teacher = None

    entries = teacher_entries(
        teacher
    )

    return render(
        request,
        "scheduling/teacher_published_timetable.html",
        {
            "teacher": teacher,
            "entries": entries,
        }
    )

