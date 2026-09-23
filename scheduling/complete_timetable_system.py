from collections import defaultdict
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from scheduling.models import (
    Day,
    Period,
    Room,
    Subject,
    Teacher,
    TeacherTeachingAssignment,
    TimetableAssignmentGroup,
    TimetableAssignmentMember,
    TimetableEntry,
    TimetableSlotRule,
    TimetableVersion,
)


SLOT_LESSON = TimetableSlotRule.TYPE_LESSON
SLOT_BREAK = TimetableSlotRule.TYPE_BREAK
SLOT_LUNCH = TimetableSlotRule.TYPE_LUNCH
SLOT_GAMES = TimetableSlotRule.TYPE_GAMES
SLOT_ACTIVITY = TimetableSlotRule.TYPE_ACTIVITY


@dataclass
class Requirement:
    assignment_id: int
    class_name: str
    stream: str
    subject_id: int
    teacher_id: int
    lesson_number: int
    is_double: bool = False
    joint_group_id: int = None


def class_key(class_name, stream):
    return (
        class_name,
        stream or "",
    )


def current_draft():
    return (
        TimetableVersion.objects
        .filter(
            status=TimetableVersion.STATUS_DRAFT
        )
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )


def published_version():
    return (
        TimetableVersion.objects
        .filter(
            status=TimetableVersion.STATUS_PUBLISHED
        )
        .order_by(
            "-published_at",
            "-id",
        )
        .first()
    )


def get_days():
    return list(
        Day.objects.all().order_by("order")
    )


def get_periods():
    return list(
        Period.objects.all().order_by("order")
    )


def get_slot_rules():
    return {
        (
            rule.day_id,
            rule.period_id,
        ): rule
        for rule in TimetableSlotRule.objects.filter(
            is_enabled=True
        ).select_related(
            "day",
            "period",
        )
    }


def usable_periods_for_day(day):
    rules = get_slot_rules()

    result = []

    for period in get_periods():

        rule = rules.get(
            (
                day.id,
                period.id,
            )
        )

        if rule:
            if rule.slot_type != SLOT_LESSON:
                continue

        elif period.is_break:
            continue

        result.append(period)

    return result


def teaching_periods():
    result = []

    for period in get_periods():
        if period.is_break:
            continue

        has_lesson_rule = TimetableSlotRule.objects.filter(
            period=period,
            is_enabled=True,
            slot_type=SLOT_LESSON,
        ).exists()

        has_non_lesson_rule = TimetableSlotRule.objects.filter(
            period=period,
            is_enabled=True,
        ).exclude(
            slot_type=SLOT_LESSON
        ).exists()

        if has_non_lesson_rule and not has_lesson_rule:
            continue

        result.append(period)

    return result


def build_assignment_requirements():
    requirements = []

    assignments = list(
        TeacherTeachingAssignment.objects.filter(
            is_active=True,
        ).select_related(
            "teacher",
            "subject",
        )
    )

    for assignment in assignments:

        frequency = max(
            1,
            int(
                assignment.lessons_per_week or 1
            )
        )

        for number in range(
            1,
            frequency + 1,
        ):
            requirements.append(
                Requirement(
                    assignment_id=assignment.id,
                    class_name=assignment.class_name,
                    stream=assignment.stream or "",
                    subject_id=assignment.subject_id,
                    teacher_id=assignment.teacher_id,
                    lesson_number=number,
                    is_double=False,
                )
            )

    return requirements


def _period_consecutive(period_a, period_b):
    if not period_a or not period_b:
        return False

    return abs(
        period_a.order -
        period_b.order
    ) == 1


def _entry_conflicts(
    entries,
    class_name,
    stream,
    teacher_id,
    room_id,
    day_id,
    period_id,
):
    class_key_value = class_key(
        class_name,
        stream,
    )

    for entry in entries:

        if entry.day_id != day_id:
            continue

        if entry.period_id != period_id:
            continue

        if class_key(
            entry.class_name,
            entry.stream,
        ) == class_key_value:
            return True

        if teacher_id and entry.teacher_id == teacher_id:
            return True

        if room_id and entry.room_id == room_id:
            return True

    return False


def check_timetable(version=None):
    if version is None:
        version = current_draft()

    requirements = build_assignment_requirements()

    if version is None:
        entries = []
    else:
        entries = list(
            TimetableEntry.objects.filter(
                version=version,
                is_active=True,
            ).select_related(
                "subject",
                "teacher",
                "day",
                "period",
                "room",
            )
        )

    problems = []

    required_counts = defaultdict(int)
    scheduled_counts = defaultdict(int)

    for requirement in requirements:

        key = (
            requirement.class_name,
            requirement.stream or "",
            requirement.subject_id,
            requirement.teacher_id,
        )

        required_counts[key] += 1

    for entry in entries:

        key = (
            entry.class_name,
            entry.stream or "",
            entry.subject_id,
            entry.teacher_id,
        )

        scheduled_counts[key] += 1

        rule = TimetableSlotRule.objects.filter(
            day=entry.day,
            period=entry.period,
            is_enabled=True,
        ).first()

        if rule and rule.slot_type != SLOT_LESSON:
            problems.append({
                "category": "Invalid slot",
                "message": (
                    f"{entry.class_name} "
                    f"{entry.stream or ''} "
                    f"{entry.subject} is scheduled "
                    f"in a {rule.get_slot_type_display()} period."
                ),
            })

        if not entry.teacher_id:
            problems.append({
                "category": "Missing teacher",
                "message": (
                    f"{entry.class_name} "
                    f"{entry.stream or ''} "
                    f"{entry.subject} has no teacher."
                ),
            })

    for key, required in required_counts.items():

        scheduled = scheduled_counts.get(
            key,
            0,
        )

        if scheduled < required:

            class_name, stream, subject_id, teacher_id = key

            problems.append({
                "category": "Unscheduled lesson",
                "message": (
                    f"{class_name} "
                    f"{stream} "
                    f"subject {subject_id} "
                    f"teacher {teacher_id} "
                    f"requires {required} lesson(s) "
                    f"but only {scheduled} are scheduled."
                ),
            })

    seen_class = set()
    seen_teacher = set()
    seen_room = set()

    for entry in entries:

        class_identifier = (
            entry.day_id,
            entry.period_id,
            entry.class_name,
            entry.stream or "",
        )

        if class_identifier in seen_class:
            problems.append({
                "category": "Class collision",
                "message": (
                    f"{entry.class_name} "
                    f"{entry.stream or ''} has more than "
                    f"one lesson in the same period."
                ),
            })

        seen_class.add(class_identifier)

        if entry.teacher_id:

            teacher_identifier = (
                entry.day_id,
                entry.period_id,
                entry.teacher_id,
            )

            if teacher_identifier in seen_teacher:
                problems.append({
                    "category": "Teacher collision",
                    "message": (
                        f"{entry.teacher} is assigned "
                        f"to more than one class at the "
                        f"same time."
                    ),
                })

            seen_teacher.add(
                teacher_identifier
            )

        if entry.room_id:

            room_identifier = (
                entry.day_id,
                entry.period_id,
                entry.room_id,
            )

            if room_identifier in seen_room:
                problems.append({
                    "category": "Room collision",
                    "message": (
                        f"{entry.room} is occupied "
                        f"more than once at the same time."
                    ),
                })

            seen_room.add(
                room_identifier
            )

    return {
        "valid": len(problems) == 0,
        "ready": len(problems) == 0,
        "required_lessons": len(requirements),
        "scheduled_lessons": len(entries),
        "total_problems": len(problems),
        "problems": problems,
    }


def generate_draft(clear_existing_draft=False):

    requirements = build_assignment_requirements()

    if not requirements:
        raise ValidationError(
            "No active teaching assignments exist."
        )

    with transaction.atomic():

        old_draft = current_draft()

        if (
            clear_existing_draft
            and old_draft is not None
        ):

            TimetableEntry.objects.filter(
                version=old_draft,
                is_active=True,
                is_fixed=False,
            ).update(
                is_active=False,
                is_published=False,
            )

            old_draft.status = (
                TimetableVersion.STATUS_ARCHIVED
            )

            old_draft.archived_at = timezone.now()

            old_draft.save(
                update_fields=[
                    "status",
                    "archived_at",
                ]
            )

        draft = TimetableVersion.objects.create(
            name=(
                "Automatic Timetable Draft "
                f"{timezone.now():%Y-%m-%d %H:%M}"
            ),
            status=TimetableVersion.STATUS_DRAFT,
        )

        fixed_entries = list(
            TimetableEntry.objects.filter(
                is_active=True,
                is_fixed=True,
            )
        )

        generated = []

        occupied_class = set()
        occupied_teacher = set()
        occupied_room = set()

        for entry in fixed_entries:

            occupied_class.add(
                (
                    entry.day_id,
                    entry.period_id,
                    entry.class_name,
                    entry.stream or "",
                )
            )

            if entry.teacher_id:
                occupied_teacher.add(
                    (
                        entry.day_id,
                        entry.period_id,
                        entry.teacher_id,
                    )
                )

            if entry.room_id:
                occupied_room.add(
                    (
                        entry.day_id,
                        entry.period_id,
                        entry.room_id,
                    )
                )

        class_day_load = defaultdict(int)
        teacher_day_load = defaultdict(int)
        period_load = defaultdict(int)

        class_subject_days = defaultdict(set)

        rooms = list(
            Room.objects.filter(
                is_active=True
            ).order_by("name")
        )

        days = get_days()

        requirements = sorted(
            requirements,
            key=lambda item: (
                -item.is_double,
                item.class_name,
                item.stream,
                item.subject_id,
                item.teacher_id,
                item.lesson_number,
            ),
        )

        unscheduled = []

        for requirement in requirements:

            candidates = []

            for day in days:

                available_periods = (
                    usable_periods_for_day(day)
                )

                for period in available_periods:

                    class_identifier = (
                        day.id,
                        period.id,
                        requirement.class_name,
                        requirement.stream or "",
                    )

                    teacher_identifier = (
                        day.id,
                        period.id,
                        requirement.teacher_id,
                    )

                    if class_identifier in occupied_class:
                        continue

                    if teacher_identifier in occupied_teacher:
                        continue

                    room = None

                    if rooms:

                        for possible_room in rooms:

                            room_identifier = (
                                day.id,
                                period.id,
                                possible_room.id,
                            )

                            if room_identifier not in occupied_room:
                                room = possible_room
                                break

                    score = 0

                    class_day = class_day_load[
                        (
                            requirement.class_name,
                            requirement.stream or "",
                            day.id,
                        )
                    ]

                    teacher_day = teacher_day_load[
                        (
                            requirement.teacher_id,
                            day.id,
                        )
                    ]

                    school_period = period_load[
                        period.id
                    ]

                    score += class_day * 1000
                    score += teacher_day * 400
                    score += school_period * 500

                    subject_day_key = (
                        (
                            requirement.class_name,
                            requirement.stream or "",
                        ),
                        requirement.subject_id,
                    )

                    if day.id in class_subject_days[
                        subject_day_key
                    ]:
                        score += 6000
                    else:
                        score -= 250

                    for existing in generated:

                        if (
                            existing.class_name
                            != requirement.class_name
                        ):
                            continue

                        if (
                            (existing.stream or "")
                            != (requirement.stream or "")
                        ):
                            continue

                        if (
                            existing.subject_id
                            != requirement.subject_id
                        ):
                            continue

                        if existing.day_id != day.id:
                            continue

                        if _period_consecutive(
                            existing.period,
                            period,
                        ):
                            score += 10000

                    score += period.order * 0.01
                    score += day.order * 0.001

                    candidates.append(
                        (
                            score,
                            day,
                            period,
                            room,
                        )
                    )

            if not candidates:

                unscheduled.append({
                    "class_name":
                        requirement.class_name,
                    "stream":
                        requirement.stream,
                    "subject_id":
                        requirement.subject_id,
                    "teacher_id":
                        requirement.teacher_id,
                    "reason":
                        "No suitable slot remained after "
                        "applying timetable constraints.",
                })

                continue

            candidates.sort(
                key=lambda item: (
                    item[0],
                    item[1].order,
                    item[2].order,
                )
            )

            _, day, period, room = candidates[0]

            entry = TimetableEntry.objects.create(
                class_name=requirement.class_name,
                stream=requirement.stream or None,
                subject_id=requirement.subject_id,
                teacher_id=requirement.teacher_id,
                day=day,
                period=period,
                room=room,
                version=draft,
                notes="Automatically generated draft",
                is_double_period=requirement.is_double,
                is_fixed=False,
                is_published=False,
                is_active=True,
            )

            generated.append(entry)

            occupied_class.add(
                (
                    day.id,
                    period.id,
                    requirement.class_name,
                    requirement.stream or "",
                )
            )

            occupied_teacher.add(
                (
                    day.id,
                    period.id,
                    requirement.teacher_id,
                )
            )

            if room:
                occupied_room.add(
                    (
                        day.id,
                        period.id,
                        room.id,
                    )
                )

            class_day_load[
                (
                    requirement.class_name,
                    requirement.stream or "",
                    day.id,
                )
            ] += 1

            teacher_day_load[
                (
                    requirement.teacher_id,
                    day.id,
                )
            ] += 1

            period_load[
                period.id
            ] += 1

            class_subject_days[
                (
                    (
                        requirement.class_name,
                        requirement.stream or "",
                    ),
                    requirement.subject_id,
                )
            ].add(day.id)

        return {
            "version": draft,
            "total_required": len(requirements),
            "scheduled": len(generated),
            "unscheduled": unscheduled,
            "fixed_preserved": len(fixed_entries),
        }


def publish_draft(version=None):

    if version is None:
        version = current_draft()

    if version is None:
        raise ValidationError(
            "There is no timetable draft to publish."
        )

    validation = check_timetable(version)

    if not validation["ready"]:
        raise ValidationError(
            "The timetable cannot be published while "
            "validation problems exist."
        )

    with transaction.atomic():

        old = published_version()

        if old and old.id != version.id:

            TimetableEntry.objects.filter(
                version=old,
                is_active=True,
            ).update(
                is_published=False
            )

            old.status = (
                TimetableVersion.STATUS_ARCHIVED
            )

            old.archived_at = timezone.now()

            old.save(
                update_fields=[
                    "status",
                    "archived_at",
                ]
            )

        version.status = (
            TimetableVersion.STATUS_PUBLISHED
        )

        version.published_at = timezone.now()

        version.save(
            update_fields=[
                "status",
                "published_at",
            ]
        )

        TimetableEntry.objects.filter(
            version=version,
            is_active=True,
        ).update(
            is_published=True
        )

    return version


def unpublish():

    version = published_version()

    if version is None:
        return 0

    with transaction.atomic():

        count = TimetableEntry.objects.filter(
            version=version,
            is_active=True,
            is_published=True,
        ).update(
            is_published=False
        )

        version.status = (
            TimetableVersion.STATUS_ARCHIVED
        )

        version.archived_at = timezone.now()

        version.save(
            update_fields=[
                "status",
                "archived_at",
            ]
        )

    return count


def published_entries():

    version = published_version()

    if version is None:
        return TimetableEntry.objects.none()

    return (
        TimetableEntry.objects
        .filter(
            version=version,
            is_active=True,
            is_published=True,
        )
        .select_related(
            "subject",
            "teacher",
            "day",
            "period",
            "room",
        )
        .order_by(
            "day__order",
            "period__order",
            "class_name",
            "stream",
        )
    )


def class_entries(
    class_name,
    stream=None,
):
    entries = published_entries().filter(
        class_name=class_name
    )

    if stream:
        entries = entries.filter(
            stream=stream
        )

    return entries


def teacher_entries(teacher):
    if not teacher:
        return TimetableEntry.objects.none()

    return published_entries().filter(
        teacher=teacher
    )


def grid(entries):

    days = get_days()
    periods = get_periods()

    cells = {}

    for entry in entries:

        cells[
            (
                entry.day_id,
                entry.period_id,
            )
        ] = entry

    return {
        "days": days,
        "periods": periods,
        "cells": cells,
    }
