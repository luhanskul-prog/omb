from datetime import datetime, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from academic.models import Stream, Subject as AcademicSubject
from fees.models import AcademicYear, Term
from students.models import Student

from .models import (
    Day,
    Teacher,
    Subject,
    TeacherClassAssignment,
    TeacherTeachingAssignment,
    TimetableAssignmentGroup,
    TimetableAssignmentMember,
    TimetableConfiguration,
    TimetableConfiguredSlot,
)


# ================================================================
# COMMON HELPERS
# ================================================================

def _display_object(obj):
    """
    Safely obtain a human-readable name from an ERP object.
    """
    for field in (
        "name",
        "full_name",
        "teacher_name",
        "subject_name",
        "class_name",
        "title",
        "code",
    ):
        value = getattr(obj, field, None)
        if value:
            return str(value)

    return str(obj)


def _active_years():
    return AcademicYear.objects.filter(is_active=True).order_by("-year")


def _active_terms():
    return Term.objects.filter(is_active=True).order_by("order", "id")


def _time_choices():
    """
    Generate time choices dynamically in 15-minute intervals.
    The choices are generated here rather than stored as fixed
    timetable periods.
    """
    choices = []

    current = datetime(2000, 1, 1, 0, 0)

    for _ in range(96):
        value = current.strftime("%H:%M")
        label = current.strftime("%I:%M %p").lstrip("0")
        choices.append((value, label))
        current += timedelta(minutes=15)

    return choices


def _parse_time(value, ampm):
    """
    Convert a 12-hour time + AM/PM selection into a Python time.
    """
    if not value:
        raise ValueError("Time is required.")

    parsed = datetime.strptime(
        f"{value} {ampm}",
        "%I:%M %p"
    )

    return parsed.time()


def _duration_minutes(start_time, end_time):
    start = datetime.combine(datetime.today(), start_time)
    end = datetime.combine(datetime.today(), end_time)

    if end <= start:
        raise ValueError("Ending time must be later than starting time.")

    return int((end - start).total_seconds() / 60)


# ================================================================
# MAIN SCHEDULING CENTRE
# ================================================================

def timetable_management_centre(request):

    teachers = Teacher.objects.all().order_by("id")

    streams = Stream.objects.filter(
        is_active=True
    ).order_by("name")

    subjects = AcademicSubject.objects.filter(
        is_active=True
    ).order_by("name")

    # Classes are derived from the existing teacher/class assignment
    # records because the current ERP does not use a separate Class
    # model in the scheduling configuration layer.

    classes = set()

    for model in (
        TeacherClassAssignment,
        TeacherTeachingAssignment,
    ):

        for field_name in (
            "class_name",
            "class",
            "classroom",
            "grade",
        ):

            try:
                field = model._meta.get_field(field_name)
            except Exception:
                continue

            try:
                values = (
                    model.objects
                    .values_list(field_name, flat=True)
                    .distinct()
                )

                for value in values:
                    if value:
                        classes.add(str(value))

            except Exception:
                pass

    context = {
        "teachers": teachers,
        "streams": streams,
        "subjects": subjects,
        "classes": sorted(classes),
        "teacher_count": teachers.count(),
        "stream_count": streams.count(),
        "subject_count": subjects.count(),
        "class_count": classes.count(),
    }

    return render(
        request,
        "scheduling/timetable_management_centre.html",
        context,
    )


# ================================================================
# YEAR + TERM SELECTION
# ================================================================

def timetable_create_select(request):

    years = _active_years()
    terms = _active_terms()

    if request.method == "POST":

        year_id = request.POST.get("academic_year")
        term_id = request.POST.get("term")

        year = get_object_or_404(
            AcademicYear,
            pk=year_id,
            is_active=True,
        )

        term = get_object_or_404(
            Term,
            pk=term_id,
            is_active=True,
        )

        configuration = (
            TimetableConfiguration.objects
            .filter(
                academic_year=year,
                term=term,
            )
            .order_by("-id")
            .first()
        )

        if configuration is None:

            configuration = TimetableConfiguration.objects.create(
                academic_year=year,
                term=term,
                name=f"Timetable Configuration - {year.year} - {term.name}",
                is_active=True,
            )

            messages.success(
                request,
                "Timetable configuration created successfully."
            )

        else:

            messages.info(
                request,
                "Existing timetable configuration loaded."
            )

        return redirect(
            "scheduling:timetable_slot_configuration",
            configuration_id=configuration.id,
        )

    return render(
        request,
        "scheduling/timetable_create_select.html",
        {
            "years": years,
            "terms": terms,
        },
    )


# ================================================================
# PERIOD / SLOT CONFIGURATION
# ================================================================

def timetable_slot_configuration(request, configuration_id):

    configuration = get_object_or_404(
        TimetableConfiguration,
        pk=configuration_id,
    )

    slots = (
        TimetableConfiguredSlot.objects
        .filter(configuration=configuration)
        .order_by("period_number", "start_time")
    )


    return render(
        request,
        "scheduling/timetable_slot_configuration.html",
        {
            "configuration": configuration,
            "slots": slots,
            "time_choices": _time_choices(),
            "slot_types": TimetableConfiguredSlot.TYPE_CHOICES,
        },
    )


def timetable_slot_add(request, configuration_id):
    configuration = get_object_or_404(
        TimetableConfiguration,
        pk=configuration_id,
    )

    if request.method == "POST":

        start_time_value = request.POST.get("start_time")
        end_time_value = request.POST.get("end_time")
        slot_type = request.POST.get("slot_type")
        notes = request.POST.get("notes", "").strip()
        is_enabled = request.POST.get("is_enabled") == "on"

        # ----------------------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------------------

        if not start_time_value or not end_time_value:
            messages.error(
                request,
                "Please select both a starting time and an ending time."
            )
            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )


        # ----------------------------------------------------
        # AUTOMATIC PERIOD / SLOT NUMBER
        #
        # The user does not enter this number.
        # It is generated sequentially within this configuration.
        # ----------------------------------------------------

        last_slot = (
            TimetableConfiguredSlot.objects
            .filter(configuration=configuration)
            .order_by("-period_number")
            .first()
        )

        period_number = (
            last_slot.period_number + 1
            if last_slot
            else 1
        )

        # ----------------------------------------------------
        # FLEXIBLE TIME PARSING
        #
        # HTML <input type="time"> submits HH:MM.
        # No 15-minute restriction is applied.
        #
        # Examples:
        # 08:00
        # 08:13
        # 12:01
        # 14:37
        # ----------------------------------------------------

        try:
            start_time = datetime.strptime(
                start_time_value,
                "%H:%M",
            ).time()

            end_time = datetime.strptime(
                end_time_value,
                "%H:%M",
            ).time()

        except ValueError:
            messages.error(
                request,
                "Please enter valid starting and ending times."
            )
            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )

        # ----------------------------------------------------
        # TIME ORDER
        # ----------------------------------------------------

        if end_time <= start_time:
            messages.error(
                request,
                "Ending time must be later than the starting time."
            )
            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )

        # ----------------------------------------------------
        # DURATION
        # ----------------------------------------------------

        duration_minutes = (
            datetime.combine(
                datetime.today(),
                end_time,
            )
            -
            datetime.combine(
                datetime.today(),
                start_time,
            )
        ).seconds // 60

        if duration_minutes <= 0:
            messages.error(
                request,
                "The calculated duration must be greater than zero."
            )
            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )

        # ----------------------------------------------------
        # SLOT TYPE
        # ----------------------------------------------------

        valid_slot_types = {
            TimetableConfiguredSlot.TYPE_LESSON,
            TimetableConfiguredSlot.TYPE_BREAK,
            TimetableConfiguredSlot.TYPE_LUNCH,
            TimetableConfiguredSlot.TYPE_GAMES,
            TimetableConfiguredSlot.TYPE_ACTIVITY,
            TimetableConfiguredSlot.TYPE_ASSEMBLY,
        }

        if slot_type not in valid_slot_types:
            messages.error(
                request,
                "Invalid timetable slot type."
            )
            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )

        # ----------------------------------------------------
        # AUTOMATIC INTERNAL SLOT NAME
        #
        # The user no longer enters a slot name.
        # The database field remains available internally.
        # ----------------------------------------------------

        type_labels = {
            TimetableConfiguredSlot.TYPE_LESSON: "Lesson",
            TimetableConfiguredSlot.TYPE_BREAK: "Break",
            TimetableConfiguredSlot.TYPE_LUNCH: "Lunch",
            TimetableConfiguredSlot.TYPE_GAMES: "Games",
            TimetableConfiguredSlot.TYPE_ACTIVITY: "Activity",
            TimetableConfiguredSlot.TYPE_ASSEMBLY: "Assembly",
        }

        slot_label = type_labels.get(slot_type, "Slot")

        period_name = f"{slot_label} {period_number}"

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        try:

            TimetableConfiguredSlot.objects.create(
                configuration=configuration,
                period_number=period_number,
                period_name=period_name,
                start_time=start_time,
                end_time=end_time,
                slot_type=slot_type,
                is_enabled=is_enabled,
                notes=notes,
            )

        except Exception as exc:

            messages.error(
                request,
                f"Unable to save this timetable slot: {exc}"
            )

            return redirect(
                "scheduling:timetable_slot_configuration",
                configuration_id=configuration.id,
            )

        messages.success(
            request,
            f"{period_name} saved successfully "
            f"({duration_minutes} minutes)."
        )

        return redirect(
            "scheduling:timetable_slot_configuration",
            configuration_id=configuration.id,
        )

    return redirect(
        "scheduling:timetable_slot_configuration",
        configuration_id=configuration.id,
    )
def timetable_slot_delete(request, slot_id):

    slot = get_object_or_404(
        TimetableConfiguredSlot,
        pk=slot_id,
    )

    configuration_id = slot.configuration_id

    if request.method == "POST":
        slot.delete()

        messages.success(
            request,
            "Period / Slot removed from the configuration."
        )

    return redirect(
        "scheduling:timetable_slot_configuration",
        configuration_id=configuration_id,
    )


# ================================================================
# ASSIGN LESSONS
# ================================================================

def timetable_assign_lessons(request, configuration_id):

    configuration = get_object_or_404(
        TimetableConfiguration,
        pk=configuration_id,
    )

    teachers = Teacher.objects.all().order_by("id")

    subjects = Subject.objects.all().order_by("id")

    # Classes are pulled directly from existing ERP student records.
    # Users do not type arbitrary class names.
    classes = (
        Student.objects
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    # Keep only real class/stream combinations already present
    # in the ERP student records.
    class_streams = (
        Student.objects
        .filter(stream__isnull=False)
        .exclude(stream="")
        .values("class_name", "stream")
        .distinct()
        .order_by("class_name", "stream")
    )

    assignments = (
        TimetableAssignmentGroup.objects
        .filter(
            configuration=configuration,
            is_active=True,
        )
        .prefetch_related("members")
        .order_by("class_name", "stream", "id")
    )

    return render(
        request,
        "scheduling/timetable_assign_lessons.html",
        {
            "configuration": configuration,
            "teachers": teachers,
            "subjects": subjects,
            "classes": classes,
            "class_streams": class_streams,
            "assignments": assignments,
        },
    )


def timetable_assignment_add(request, configuration_id):

    configuration = get_object_or_404(
        TimetableConfiguration,
        pk=configuration_id,
    )

    if request.method != "POST":
        return redirect(
            "scheduling:timetable_assign_lessons",
            configuration_id=configuration.id,
        )

    class_name = request.POST.get(
        "class_name",
        ""
    ).strip()

    stream = request.POST.get(
        "stream",
        ""
    ).strip()

    teacher_id = request.POST.get("teacher")
    subject_id = request.POST.get("subject")

    lessons_per_week = request.POST.get(
        "lessons_per_week",
        "1"
    )

    mode = request.POST.get(
        "mode",
        "SEPARATE"
    )

    duration = request.POST.get(
        "duration",
        ""
    ).strip()

    notes = request.POST.get(
        "notes",
        ""
    ).strip()

    try:

        if not class_name:
            raise ValueError("Class is required.")

        if not Student.objects.filter(class_name=class_name).exists():
            raise ValueError(
                "Please select a class from the existing ERP classes."
            )

        if not teacher_id:
            raise ValueError("Teacher is required.")

        if not subject_id:
            raise ValueError("Subject is required.")

        lessons_per_week = int(lessons_per_week)

        if lessons_per_week <= 0:
            raise ValueError(
                "Lessons per week must be greater than zero."
            )

        teacher = get_object_or_404(
            Teacher,
            pk=teacher_id,
        )

        subject = get_object_or_404(
            Subject,
            pk=subject_id,
        )

        group = TimetableAssignmentGroup.objects.create(
            configuration=configuration,
            class_name=class_name,
            stream=stream,
            lessons_per_week=lessons_per_week,
            mode=mode,
            duration=duration,
            is_active=True,
            notes=notes,
        )

        TimetableAssignmentMember.objects.create(
            group=group,
            teacher=teacher,
            subject=subject,
            is_active=True,
        )

        messages.success(
            request,
            "Lesson assignment saved successfully."
        )

    except Exception as exc:

        messages.error(
            request,
            str(exc),
        )

    return redirect(
        "scheduling:timetable_assign_lessons",
        configuration_id=configuration.id,
    )


def timetable_assignment_delete(request, configuration_id, assignment_id):

    assignment = get_object_or_404(
        TimetableAssignmentGroup,
        pk=assignment_id,
    )

    if request.method == "POST":

        assignment.is_active = False
        assignment.save(update_fields=["is_active"])

        messages.success(
            request,
            "Lesson assignment removed."
        )

    return redirect(
        "scheduling:timetable_assign_lessons",
        configuration_id=configuration_id,
    )


# ================================================================
# DATA DIRECTORY PAGES
# ================================================================

def timetable_teachers(request):

    teachers = Teacher.objects.all().order_by("id")

    return render(
        request,
        "scheduling/timetable_data_list.html",
        {
            "page_title": "Teachers",
            "page_subtitle": "Teachers pulled from the ERP administration records.",
            "objects": teachers,
            "object_type": "teacher",
        },
    )


def timetable_subjects(request):

    subjects = Subject.objects.all().order_by("id")

    return render(
        request,
        "scheduling/timetable_data_list.html",
        {
            "page_title": "Subjects",
            "page_subtitle": "Subjects pulled from the ERP administration records.",
            "objects": subjects,
            "object_type": "subject",
        },
    )


def timetable_streams(request):

    streams = Stream.objects.filter(
        is_active=True
    ).order_by("name")

    return render(
        request,
        "scheduling/timetable_data_list.html",
        {
            "page_title": "Streams",
            "page_subtitle": "Streams pulled from the ERP administration records.",
            "objects": streams,
            "object_type": "stream",
        },
    )


def timetable_classes(request):

    classes = (
        Student.objects
        .values_list("class_name", flat=True)
        .distinct()
        .order_by("class_name")
    )

    return render(
        request,
        "scheduling/timetable_data_list.html",
        {
            "page_title": "Classes",
            "page_subtitle": "Classes pulled from existing ERP student records.",
            "objects": classes,
            "object_type": "class",
        },
    )

    return render(
        request,
        "scheduling/timetable_data_list.html",
        {
            "page_title": "Classes",
            "page_subtitle": "Classes pulled from existing ERP teaching/class assignment records.",
            "objects": sorted(classes),
            "object_type": "class",
        },
    )















