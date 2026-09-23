from collections import defaultdict
from django.db import transaction
from django.utils import timezone

from scheduling.models import (
    Day,
    Period,
    Room,
    TeacherTeachingAssignment,
    TimetableEntry,
    TimetableVersion,
)


def _class_key(class_name, stream):
    return (class_name, stream or "")


def _period_is_consecutive(period_a, period_b):
    if not period_a or not period_b:
        return False

    return abs(period_a.order - period_b.order) == 1


def _build_assignment_requirements(assignments):
    requirements = []

    for assignment in assignments:
        required = max(int(assignment.lessons_per_week or 0), 0)

        if required <= 0:
            continue

        for lesson_number in range(1, required + 1):
            requirements.append(
                {
                    "assignment": assignment,
                    "lesson_number": lesson_number,
                }
            )

    return requirements


def _candidate_score(
    day,
    period,
    class_key,
    teacher_id,
    subject_id,
    class_day_load,
    teacher_day_load,
    day_load,
    class_subject_days,
    class_subject_slots,
    period_by_id,
    class_day_periods,
    teacher_day_periods,
):
    score = 0

    class_load = class_day_load[(class_key, day.id)]
    teacher_load = teacher_day_load[(teacher_id, day.id)]
    school_day_load = day_load[day.id]

    subject_days = class_subject_days[(class_key, subject_id)]

    # Primary objective:
    # spread lessons for the same class across the week.
    score += class_load * 1000

    # Secondary objective:
    # prevent excessive teacher concentration.
    score += teacher_load * 350

    # Balance the whole school timetable.
    score += school_day_load * 20

    # ----------------------------------------------------------
    # PERIOD DISTRIBUTION
    # ----------------------------------------------------------
    # Do not allow otherwise equivalent lessons to pile into
    # the first available period of every day.
    #
    # The generator should use the school day naturally rather
    # than always selecting Period 1 whenever no hard conflict
    # exists.
    #
    # A period with more lessons already assigned receives a
    # penalty. This encourages the timetable to spread lessons
    # through the available teaching periods.
    period_load = sum(
        1
        for existing_period_id in (
            entry_period_id
            for (
                existing_day_id,
                existing_period_id,
            ) in class_day_periods[(class_key, day.id)]
        )
        if existing_period_id == period.id
    )

    score += period_load * 250

    # Mild position penalty prevents Period 1 from winning every
    # otherwise-equal comparison while still allowing earlier
    # periods to be used normally.
    score += period.order * 2

    # Strongly prefer a new day for a repeated subject.
    if day.id in subject_days:
        score += 5000
    else:
        score -= 150

    # Avoid placing the same subject in consecutive periods.
    # class_subject_slots stores (day_id, period_id),
    # so convert the stored period ID back to its Period object.
    existing_subject_slots = class_subject_slots[
        (class_key, subject_id)
    ]

    for existing_day_id, existing_period_id in existing_subject_slots:
        if existing_day_id != day.id:
            continue

        existing_period = period_by_id.get(existing_period_id)

        if existing_period is not None:
            if _period_is_consecutive(existing_period, period):
                score += 10000

    # Avoid placing lessons next to each other unnecessarily
    # when the class already has a busy day.
    class_period_orders = class_day_periods[
        (class_key, day.id)
    ]

    for existing_order in class_period_orders:
        if abs(existing_order - period.order) == 1:
            score += 35

    # Avoid unnecessary teacher back-to-back teaching.
    teacher_period_orders = teacher_day_periods[
        (teacher_id, day.id)
    ]

    for existing_order in teacher_period_orders:
        if abs(existing_order - period.order) == 1:
            score += 15

    # Prefer middle/earlier periods only as a final tie breaker.
    score += period.order * 0.01
    score += day.order * 0.001

    return score


def _conflict_reason(
    assignment,
    days,
    teaching_periods,
    occupied_classes,
    occupied_teachers,
    occupied_rooms,
    rooms,
):
    class_key = _class_key(
        assignment.class_name,
        assignment.stream,
    )

    possible_class_slots = 0
    possible_teacher_slots = 0
    possible_room_slots = 0

    for day in days:
        for period in teaching_periods:
            class_slot = (
                day.id,
                period.id,
                class_key,
            )

            teacher_slot = (
                day.id,
                period.id,
                assignment.teacher_id,
            )

            if class_slot in occupied_classes:
                continue

            possible_class_slots += 1

            if teacher_slot in occupied_teachers:
                continue

            possible_teacher_slots += 1

            if not rooms:
                possible_room_slots += 1
                continue

            room_available = any(
                (
                    day.id,
                    period.id,
                    room.id,
                ) not in occupied_rooms
                for room in rooms
            )

            if room_available:
                possible_room_slots += 1

    if possible_class_slots == 0:
        return (
            "No free class slot remains for "
            f"{assignment.class_name} "
            f"{assignment.stream or ''}."
        )

    if possible_teacher_slots == 0:
        return (
            "No free teacher slot remains for "
            f"{assignment.teacher}."
        )

    if possible_room_slots == 0:
        return (
            "No free room remains for the required periods."
        )

    return (
        "No suitable slot remained after applying "
        "the timetable constraints."
    )


def generate_timetable(clear_existing_draft=False):
    """
    Generate an automatic timetable draft.

    Hard constraints:
    - A class/stream cannot have two lessons at once.
    - A teacher cannot teach two classes at once.
    - A room cannot be used twice at once.
    - Break periods are excluded.
    - Fixed timetable entries are preserved.

    Soft constraints:
    - Spread lessons across the school week.
    - Spread repeated subjects across different days.
    - Avoid consecutive periods for the same subject.
    - Balance class workload by day.
    - Balance teacher workload by day.
    - Balance overall school usage by day.
    - Avoid unnecessary back-to-back class/teacher periods.
    """

    days = list(
        Day.objects.all()
        .order_by("order", "id")
    )

    teaching_periods = list(
        Period.objects
        .filter(is_break=False)
        .order_by("order", "id")
    )

    period_by_id = {
        period.id: period
        for period in teaching_periods
    }

    rooms = list(
        Room.objects
        .filter(is_active=True)
        .order_by("name", "id")
    )

    assignments = list(
        TeacherTeachingAssignment.objects
        .select_related("teacher", "subject")
        .filter(
            is_active=True,
            teacher__is_active=True,
            subject__is_active=True,
        )
        .order_by(
            "class_name",
            "stream",
            "teacher__name",
            "subject__name",
            "id",
        )
    )

    fixed_entries = list(
        TimetableEntry.objects
        .select_related(
            "teacher",
            "subject",
            "day",
            "period",
            "room",
        )
        .filter(
            is_active=True,
            is_fixed=True,
        )
    )

    total_required = sum(
        max(int(a.lessons_per_week or 0), 0)
        for a in assignments
    )

    if not days:
        return {
            "total_required": total_required,
            "scheduled": 0,
            "unscheduled": [
                {
                    "assignment": a,
                    "subject": a.subject,
                    "teacher": a.teacher,
                    "class_name": a.class_name,
                    "stream": a.stream,
                    "required": a.lessons_per_week,
                    "scheduled": 0,
                    "remaining": a.lessons_per_week,
                    "reason": "No school days have been configured.",
                }
                for a in assignments
            ],
            "fixed_preserved": len(fixed_entries),
        }

    if not teaching_periods:
        return {
            "total_required": total_required,
            "scheduled": 0,
            "unscheduled": [
                {
                    "assignment": a,
                    "subject": a.subject,
                    "teacher": a.teacher,
                    "class_name": a.class_name,
                    "stream": a.stream,
                    "required": a.lessons_per_week,
                    "scheduled": 0,
                    "remaining": a.lessons_per_week,
                    "reason": "No teaching periods have been configured.",
                }
                for a in assignments
            ],
            "fixed_preserved": len(fixed_entries),
        }

    # ------------------------------------------------------------
    # TIMETABLE VERSION
    # ------------------------------------------------------------
    # Automatic generation works inside a new DRAFT version.
    # Published timetable versions are never globally cleared.
    # ------------------------------------------------------------

    current_draft = (
        TimetableVersion.objects
        .filter(status=TimetableVersion.STATUS_DRAFT)
        .order_by("-created_at", "-id")
        .first()
    )

    if clear_existing_draft and current_draft is not None:
        TimetableEntry.objects.filter(
            version=current_draft,
            is_active=True,
            is_fixed=False,
        ).update(
            is_active=False,
            is_published=False,
        )

        current_draft.status = TimetableVersion.STATUS_ARCHIVED
        current_draft.archived_at = timezone.now()
        current_draft.save(
            update_fields=["status", "archived_at"]
        )

    draft_version = TimetableVersion.objects.create(
        name="Automatically Generated Timetable Draft",
        status=TimetableVersion.STATUS_DRAFT,
    )

    occupied_classes = set()
    occupied_teachers = set()
    occupied_rooms = set()

    class_day_load = defaultdict(int)
    teacher_day_load = defaultdict(int)
    day_load = defaultdict(int)

    class_subject_days = defaultdict(set)
    class_subject_slots = defaultdict(list)

    class_day_periods = defaultdict(list)
    teacher_day_periods = defaultdict(list)

    for entry in fixed_entries:
        class_key = _class_key(
            entry.class_name,
            entry.stream,
        )

        occupied_classes.add(
            (
                entry.day_id,
                entry.period_id,
                class_key,
            )
        )

        if entry.teacher_id:
            occupied_teachers.add(
                (
                    entry.day_id,
                    entry.period_id,
                    entry.teacher_id,
                )
            )

        if entry.room_id:
            occupied_rooms.add(
                (
                    entry.day_id,
                    entry.period_id,
                    entry.room_id,
                )
            )

        class_day_load[
            (class_key, entry.day_id)
        ] += 1

        if entry.teacher_id:
            teacher_day_load[
                (entry.teacher_id, entry.day_id)
            ] += 1

        day_load[entry.day_id] += 1

        class_subject_days[
            (class_key, entry.subject_id)
        ].add(entry.day_id)

        class_subject_slots[
            (class_key, entry.subject_id)
        ].append(
            (entry.day_id, entry.period_id)
        )

        class_day_periods[
            (class_key, entry.day.id)
        ].append(entry.period.order)

        if entry.teacher_id:
            teacher_day_periods[
                (entry.teacher_id, entry.day.id)
            ].append(entry.period.order)

    requirements = _build_assignment_requirements(
        assignments
    )

    # Schedule the most constrained requirements first.
    #
    # Higher weekly frequency is handled first because it has
    # fewer safe combinations once the timetable fills.
    ordered_requirements = sorted(
        requirements,
        key=lambda item: (
            -item["assignment"].lessons_per_week,
            item["assignment"].class_name,
            item["assignment"].stream or "",
            item["assignment"].subject.name,
            item["assignment"].teacher.name,
            item["assignment"].id,
            item["lesson_number"],
        )
    )

    scheduled_by_assignment = defaultdict(int)
    unscheduled = []

    with transaction.atomic():

        for requirement in ordered_requirements:

            assignment = requirement["assignment"]

            class_key = _class_key(
                assignment.class_name,
                assignment.stream,
            )

            subject_id = assignment.subject_id
            teacher_id = assignment.teacher_id

            candidates = []

            for day in days:
                for period in teaching_periods:

                    class_slot = (
                        day.id,
                        period.id,
                        class_key,
                    )

                    teacher_slot = (
                        day.id,
                        period.id,
                        teacher_id,
                    )

                    if class_slot in occupied_classes:
                        continue

                    if teacher_slot in occupied_teachers:
                        continue

                    selected_room = None

                    if rooms:
                        for room in rooms:
                            room_slot = (
                                day.id,
                                period.id,
                                room.id,
                            )

                            if room_slot not in occupied_rooms:
                                selected_room = room
                                break

                        if selected_room is None:
                            continue

                    score = _candidate_score(
                        day=day,
                        period=period,
                        class_key=class_key,
                        teacher_id=teacher_id,
                        subject_id=subject_id,
                        class_day_load=class_day_load,
                        teacher_day_load=teacher_day_load,
                        day_load=day_load,
                        class_subject_days=class_subject_days,
                        class_subject_slots=class_subject_slots,
                        class_day_periods=class_day_periods,
                        period_by_id=period_by_id,
                        teacher_day_periods=teacher_day_periods,
                    )

                    candidates.append(
                        {
                            "score": score,
                            "day": day,
                            "period": period,
                            "room": selected_room,
                        }
                    )

            if not candidates:
                unscheduled.append(
                    {
                        "assignment": assignment,
                        "subject": assignment.subject,
                        "teacher": assignment.teacher,
                        "class_name": assignment.class_name,
                        "stream": assignment.stream,
                        "required": assignment.lessons_per_week,
                        "scheduled": scheduled_by_assignment[
                            assignment.id
                        ],
                        "remaining": (
                            assignment.lessons_per_week
                            - scheduled_by_assignment[
                                assignment.id
                            ]
                        ),
                        "reason": _conflict_reason(
                            assignment,
                            days,
                            teaching_periods,
                            occupied_classes,
                            occupied_teachers,
                            occupied_rooms,
                            rooms,
                        ),
                    }
                )

                continue

            candidates.sort(
                key=lambda item: (
                    item["score"],
                    item["day"].order,
                    item["period"].order,
                )
            )

            selected = candidates[0]

            day = selected["day"]
            period = selected["period"]
            room = selected["room"]

            entry = TimetableEntry(
                class_name=assignment.class_name,
                stream=assignment.stream,
                subject=assignment.subject,
                teacher=assignment.teacher,
                day=day,
                period=period,
                room=room,
                version=draft_version,
                notes="Automatically generated draft",
                is_double_period=False,
                is_fixed=False,
                is_published=False,
                is_active=True,
            )

            entry.save()

            occupied_classes.add(
                (
                    day.id,
                    period.id,
                    class_key,
                )
            )

            occupied_teachers.add(
                (
                    day.id,
                    period.id,
                    teacher_id,
                )
            )

            if room:
                occupied_rooms.add(
                    (
                        day.id,
                        period.id,
                        room.id,
                    )
                )

            class_day_load[
                (class_key, day.id)
            ] += 1

            teacher_day_load[
                (teacher_id, day.id)
            ] += 1

            day_load[day.id] += 1

            class_subject_days[
                (class_key, subject_id)
            ].add(day.id)

            class_subject_slots[
                (class_key, subject_id)
            ].append(
                (day.id, period.id)
            )

            class_day_periods[
                (class_key, day.id)
            ].append(period.order)

            teacher_day_periods[
                (teacher_id, day.id)
            ].append(period.order)

            scheduled_by_assignment[
                assignment.id
            ] += 1

    scheduled_count = sum(
        scheduled_by_assignment.values()
    )

    return {
        "total_required": total_required,
        "scheduled": scheduled_count,
        "unscheduled": unscheduled,
        "fixed_preserved": len(fixed_entries),
    }