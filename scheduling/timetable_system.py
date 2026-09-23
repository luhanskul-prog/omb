from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Day,
    Period,
    Room,
    TeacherTeachingAssignment,
    TimetableEntry,
    TimetableVersion,
)


# ============================================================
# TIMETABLE TYPES
# ============================================================

LESSON = "LESSON"
BREAK = "BREAK"
LUNCH = "LUNCH"
GAMES = "GAMES"
ACTIVITY = "ACTIVITY"

SLOT_TYPES = {
    LESSON: "Lesson",
    BREAK: "Break",
    LUNCH: "Lunch",
    GAMES: "Games",
    ACTIVITY: "Activity",
}


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class ValidationProblem:
    category: str
    message: str
    severity: str = "ERROR"

    def as_dict(self):
        return {
            "category": self.category,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class Requirement:
    assignment_id: int
    class_name: str
    stream: str
    teacher_id: Optional[int]
    subject_id: int
    lessons_per_week: int
    is_double: bool = False


# ============================================================
# BASIC HELPERS
# ============================================================

def class_key(class_name, stream):
    return (
        str(class_name or "").strip().upper(),
        str(stream or "").strip().upper(),
    )


def period_is_consecutive(a, b):
    if not a or not b:
        return False

    return abs(int(a.order) - int(b.order)) == 1


def get_teaching_periods():
    return list(
        Period.objects
        .all()
        .order_by("order", "id")
    )


def get_lesson_periods():
    return [
        p for p in get_teaching_periods()
        if not getattr(p, "is_break", False)
    ]


def get_days():
    return list(
        Day.objects
        .all()
        .order_by("order", "id")
    )


def current_draft():
    return (
        TimetableVersion.objects
        .filter(status=TimetableVersion.STATUS_DRAFT)
        .order_by("-created_at", "-id")
        .first()
    )


def published_version():
    return (
        TimetableVersion.objects
        .filter(status=TimetableVersion.STATUS_PUBLISHED)
        .order_by("-published_at", "-id")
        .first()
    )


# ============================================================
# REQUIREMENTS
# ============================================================

def build_requirements():
    requirements = []

    assignments = (
        TeacherTeachingAssignment.objects
        .select_related("teacher", "subject")
        .all()
        .order_by(
            "class_name",
            "stream",
            "subject_id",
            "teacher_id",
            "id",
        )
    )

    for assignment in assignments:
        lessons = int(
            getattr(
                assignment,
                "lessons_per_week",
                1,
            )
            or 0
        )

        if lessons <= 0:
            continue

        for lesson_number in range(1, lessons + 1):
            requirements.append(
                Requirement(
                    assignment_id=assignment.id,
                    class_name=assignment.class_name,
                    stream=getattr(
                        assignment,
                        "stream",
                        "",
                    ) or "",
                    teacher_id=(
                        assignment.teacher_id
                        if assignment.teacher_id
                        else None
                    ),
                    subject_id=assignment.subject_id,
                    lessons_per_week=lessons,
                    is_double=False,
                )
            )

    return requirements


# ============================================================
# SLOT OCCUPANCY
# ============================================================

def occupancy_for_entries(entries):
    class_slots = defaultdict(list)
    teacher_slots = defaultdict(list)
    room_slots = defaultdict(list)

    for entry in entries:
        key = (
            entry.day_id,
            entry.period_id,
        )

        class_slots[
            (
                entry.class_name,
                entry.stream or "",
                key,
            )
        ].append(entry)

        if entry.teacher_id:
            teacher_slots[
                (
                    entry.teacher_id,
                    key,
                )
            ].append(entry)

        if entry.room_id:
            room_slots[
                (
                    entry.room_id,
                    key,
                )
            ].append(entry)

    return (
        class_slots,
        teacher_slots,
        room_slots,
    )


# ============================================================
# VALIDATION
# ============================================================

def check_timetable(version=None):
    problems = []

    if version is None:
        version = current_draft()

    entries_qs = TimetableEntry.objects.filter(
        is_active=True,
    )

    if version is not None:
        entries_qs = entries_qs.filter(
            Q(is_fixed=True)
            | Q(version=version)
            | Q(version__isnull=True)
        )

    entries = list(
        entries_qs
        .select_related(
            "day",
            "period",
            "teacher",
            "room",
            "subject",
            "version",
        )
        .order_by(
            "day__order",
            "period__order",
            "id",
        )
    )

    # --------------------------------------------------------
    # CLASS COLLISIONS
    # --------------------------------------------------------

    class_map = defaultdict(list)

    for entry in entries:
        class_map[
            (
                entry.class_name,
                entry.stream or "",
                entry.day_id,
                entry.period_id,
            )
        ].append(entry)

    for key, items in class_map.items():
        if len(items) > 1:
            names = ", ".join(
                str(item.subject)
                for item in items
            )

            problems.append(
                ValidationProblem(
                    "Class collision",
                    (
                        f"{key[0]} {key[1]} has more than one "
                        f"lesson at the same time: {names}."
                    ),
                )
            )

    # --------------------------------------------------------
    # TEACHER COLLISIONS
    # --------------------------------------------------------

    teacher_map = defaultdict(list)

    for entry in entries:
        if not entry.teacher_id:
            continue

        teacher_map[
            (
                entry.teacher_id,
                entry.day_id,
                entry.period_id,
            )
        ].append(entry)

    for key, items in teacher_map.items():
        if len(items) > 1:
            teacher_name = str(
                items[0].teacher
            )

            problems.append(
                ValidationProblem(
                    "Teacher collision",
                    (
                        f"{teacher_name} is assigned to more "
                        f"than one lesson at the same time."
                    ),
                )
            )

    # --------------------------------------------------------
    # ROOM COLLISIONS
    # --------------------------------------------------------

    room_map = defaultdict(list)

    for entry in entries:
        if not entry.room_id:
            continue

        room_map[
            (
                entry.room_id,
                entry.day_id,
                entry.period_id,
            )
        ].append(entry)

    for key, items in room_map.items():
        if len(items) > 1:
            problems.append(
                ValidationProblem(
                    "Room collision",
                    (
                        f"Room {items[0].room} is occupied by "
                        f"more than one lesson at the same time."
                    ),
                )
            )

    # --------------------------------------------------------
    # BREAK VALIDATION
    # --------------------------------------------------------

    for entry in entries:
        if getattr(entry.period, "is_break", False):
            problems.append(
                ValidationProblem(
                    "Invalid period",
                    (
                        f"{entry.class_name} {entry.stream or ''} "
                        f"has {entry.subject} assigned during "
                        f"break period {entry.period.name}."
                    ),
                )
            )

    # --------------------------------------------------------
    # TEACHER VALIDITY
    # --------------------------------------------------------

    requirements = build_requirements()

    for requirement in requirements:
        if not requirement.teacher_id:
            problems.append(
                ValidationProblem(
                    "Missing teacher",
                    (
                        f"{requirement.class_name} "
                        f"{requirement.stream}: subject "
                        f"{requirement.subject_id} has no teacher."
                    )
                )
            )

    # --------------------------------------------------------
    # UNSCHEDULED ASSIGNMENTS
    # --------------------------------------------------------

    scheduled_by_assignment = defaultdict(int)

    for entry in entries:
        if not entry.version_id:
            continue

        assignment_id = getattr(
            entry,
            "assignment_id",
            None,
        )

        if assignment_id:
            scheduled_by_assignment[
                assignment_id
            ] += 1

    # Existing architecture does not yet have assignment_id
    # on TimetableEntry, so independently compare requirements
    # by class/stream/subject/teacher.

    requirement_counts = defaultdict(int)

    for requirement in requirements:
        requirement_counts[
            (
                requirement.class_name,
                requirement.stream,
                requirement.subject_id,
                requirement.teacher_id,
            )
        ] += 1

    actual_counts = defaultdict(int)

    for entry in entries:
        actual_counts[
            (
                entry.class_name,
                entry.stream or "",
                entry.subject_id,
                entry.teacher_id,
            )
        ] += 1

    for key, required in requirement_counts.items():
        actual = actual_counts.get(key, 0)

        if actual < required:
            problems.append(
                ValidationProblem(
                    "Unscheduled lesson",
                    (
                        f"{key[0]} {key[1]} subject "
                        f"{key[2]} requires {required} lesson(s) "
                        f"but only {actual} are scheduled."
                    )
                )
            )

    # --------------------------------------------------------
    # DOUBLE PERIOD CHECK
    # --------------------------------------------------------

    period_by_id = {
        p.id: p
        for p in get_teaching_periods()
    }

    for entry in entries:
        if not entry.is_double_period:
            continue

        next_period = next(
            (
                p for p in get_teaching_periods()
                if p.order == entry.period.order + 1
                and not getattr(p, "is_break", False)
            ),
            None,
        )

        if next_period is None:
            problems.append(
                ValidationProblem(
                    "Double-period error",
                    (
                        f"{entry.class_name} "
                        f"{entry.stream or ''} "
                        f"{entry.subject} starts a double period "
                        f"at {entry.period.name}, but no valid "
                        f"consecutive lesson period exists."
                    )
                )
            )
            continue

        same_class = TimetableEntry.objects.filter(
            is_active=True,
            class_name=entry.class_name,
            stream=entry.stream,
            day=entry.day,
            period=next_period,
        ).exclude(
            pk=entry.pk
        ).exists()

        if same_class:
            problems.append(
                ValidationProblem(
                    "Double-period error",
                    (
                        f"{entry.class_name} {entry.stream or ''} "
                        f"cannot complete the double period for "
                        f"{entry.subject} because the next period "
                        f"is occupied."
                    )
                )
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    category_counts = defaultdict(int)

    for problem in problems:
        category_counts[
            problem.category
        ] += 1

    return {
        "ready": not any(
            p.severity == "ERROR"
            for p in problems
        ),
        "valid": len(problems) == 0,
        "problems": [
            p.as_dict()
            for p in problems
        ],
        "counts": dict(category_counts),
        "total_problems": len(problems),
        "required_lessons": len(requirements),
        "scheduled_lessons": len(entries),
    }


# ============================================================
# AUTOMATIC GENERATION
# ============================================================

def generate_smart_draft(
    clear_existing_draft=False,
):
    """
    Generate a fresh draft without publishing it.

    Published timetable entries are never removed here.
    """

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
                + timezone.now().strftime(
                    "%Y-%m-%d %H:%M"
                )
            ),
            status=TimetableVersion.STATUS_DRAFT,
        )

        days = get_days()
        periods = get_lesson_periods()

        fixed_entries = list(
            TimetableEntry.objects.filter(
                is_active=True,
                is_fixed=True,
            )
        )

        generated_entries = []

        class_slots = set()
        teacher_slots = set()
        room_slots = set()

        period_load = defaultdict(int)
        class_day_load = defaultdict(int)
        teacher_day_load = defaultdict(int)
        class_subject_days = defaultdict(set)
        class_subject_slots = defaultdict(list)

        for entry in fixed_entries:
            key = (
                entry.day_id,
                entry.period_id,
            )

            class_slots.add(
                (
                    entry.class_name,
                    entry.stream or "",
                    key,
                )
            )

            if entry.teacher_id:
                teacher_slots.add(
                    (
                        entry.teacher_id,
                        key,
                    )
                )

            if entry.room_id:
                room_slots.add(
                    (
                        entry.room_id,
                        key,
                    )
                )

            period_load[
                entry.period_id
            ] += 1

            class_day_load[
                (
                    entry.class_name,
                    entry.stream or "",
                    entry.day_id,
                )
            ] += 1

        requirements = build_requirements()

        # Difficult requirements first.
        requirements.sort(
            key=lambda r: (
                -int(r.is_double),
                -int(r.lessons_per_week),
                r.class_name,
                r.stream,
                r.subject_id,
                r.teacher_id or 0,
                r.assignment_id,
            )
        )

        unscheduled = []

        rooms = list(
            Room.objects
            .filter(is_active=True)
            .order_by("name", "id")
        )

        for requirement in requirements:

            best = None

            for day in days:

                for period in periods:

                    slot = (
                        day.id,
                        period.id,
                    )

                    class_key_value = (
                        requirement.class_name,
                        requirement.stream or "",
                    )

                    if (
                        class_key_value,
                        slot,
                    ) in class_slots:
                        continue

                    if (
                        requirement.teacher_id,
                        slot,
                    ) in teacher_slots:
                        continue

                    # Double lesson must have next usable period.
                    if requirement.is_double:
                        next_period = next(
                            (
                                p for p in periods
                                if p.order ==
                                period.order + 1
                            ),
                            None,
                        )

                        if next_period is None:
                            continue

                        next_slot = (
                            day.id,
                            next_period.id,
                        )

                        if (
                            class_key_value,
                            next_slot,
                        ) in class_slots:
                            continue

                        if (
                            requirement.teacher_id,
                            next_slot,
                        ) in teacher_slots:
                            continue

                    room = None

                    if rooms:
                        for candidate_room in rooms:
                            if (
                                candidate_room.id,
                                slot,
                            ) not in room_slots:
                                room = candidate_room
                                break

                    score = 0

                    # Spread classes across the week.
                    score += class_day_load[
                        (
                            requirement.class_name,
                            requirement.stream or "",
                            day.id,
                        )
                    ] * 1000

                    # Spread teacher workload.
                    score += teacher_day_load[
                        (
                            requirement.teacher_id,
                            day.id,
                        )
                    ] * 350

                    # Do not concentrate the whole school
                    # in Period 1.
                    score += (
                        period_load[period.id]
                        * 500
                    )

                    # Strongly discourage repeated subject
                    # on the same day.
                    subject_day_key = (
                        class_key_value,
                        requirement.subject_id,
                    )

                    if (
                        day.id
                        in class_subject_days[
                            subject_day_key
                        ]
                    ):
                        score += 4000
                    else:
                        score -= 500

                    # Avoid same subject consecutively.
                    for (
                        existing_day_id,
                        existing_period_id,
                    ) in class_subject_slots[
                        subject_day_key
                    ]:
                        if (
                            existing_day_id == day.id
                            and existing_period_id
                            in period_load
                        ):
                            existing_period = next(
                                (
                                    p for p in periods
                                    if p.id ==
                                    existing_period_id
                                ),
                                None,
                            )

                            if (
                                existing_period
                                and period_is_consecutive(
                                    existing_period,
                                    period,
                                )
                            ):
                                score += 10000

                    # Slightly prefer a balanced school day.
                    score += (
                        day.order * 0.01
                        + period.order * 0.001
                    )

                    candidate = {
                        "score": score,
                        "day": day,
                        "period": period,
                        "room": room,
                    }

                    if (
                        best is None
                        or candidate["score"]
                        < best["score"]
                    ):
                        best = candidate

            if best is None:
                unscheduled.append(
                    {
                        "assignment_id":
                            requirement.assignment_id,
                        "class_name":
                            requirement.class_name,
                        "stream":
                            requirement.stream,
                        "subject_id":
                            requirement.subject_id,
                        "teacher_id":
                            requirement.teacher_id,
                        "reason":
                            "No valid slot remained after "
                            "applying timetable constraints.",
                    }
                )
                continue

            day = best["day"]
            period = best["period"]
            room = best["room"]

            entry = TimetableEntry.objects.create(
                class_name=requirement.class_name,
                stream=requirement.stream,
                subject_id=requirement.subject_id,
                teacher_id=requirement.teacher_id,
                day=day,
                period=period,
                room=room,
                version=draft,
                notes=(
                    "Automatically generated draft"
                ),
                is_double_period=requirement.is_double,
                is_fixed=False,
                is_published=False,
                is_active=True,
            )

            generated_entries.append(entry)

            slot = (
                day.id,
                period.id,
            )

            class_slots.add(
                (
                    requirement.class_name,
                    requirement.stream or "",
                    slot,
                )
            )

            if requirement.teacher_id:
                teacher_slots.add(
                    (
                        requirement.teacher_id,
                        slot,
                    )
                )

            if room:
                room_slots.add(
                    (
                        room.id,
                        slot,
                    )
                )

            period_load[
                period.id
            ] += 1

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

            class_subject_days[
                (
                    (
                        requirement.class_name,
                        requirement.stream or "",
                    ),
                    requirement.subject_id,
                )
            ].add(day.id)

            class_subject_slots[
                (
                    (
                        requirement.class_name,
                        requirement.stream or "",
                    ),
                    requirement.subject_id,
                )
            ].append(
                (
                    day.id,
                    period.id,
                )
            )

        return {
            "version": draft,
            "total_required": len(requirements),
            "scheduled": len(generated_entries),
            "unscheduled": unscheduled,
            "fixed_preserved": len(fixed_entries),
        }


# ============================================================
# VERSION PUBLICATION
# ============================================================

def publish_version(version=None):
    if version is None:
        version = current_draft()

    if version is None:
        raise ValidationError(
            "There is no timetable draft to publish."
        )

    validation = check_timetable(version)

    if not validation["ready"]:
        raise ValidationError(
            "The timetable cannot be published because "
            "validation errors still exist."
        )

    with transaction.atomic():

        old = published_version()

        if old is not None:
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

            TimetableEntry.objects.filter(
                version=old,
                is_active=True,
            ).update(
                is_published=False
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


# ============================================================
# UNPUBLISH
# ============================================================

def unpublish_current_version():
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


# ============================================================
# PORTAL QUERYSETS
# ============================================================

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
            "room",
            "day",
            "period",
        )
        .order_by(
            "day__order",
            "period__order",
            "class_name",
            "stream",
        )
    )


def teacher_published_entries(teacher):
    if not teacher:
        return TimetableEntry.objects.none()

    return published_entries().filter(
        teacher=teacher
    )


def class_published_entries(
    class_name,
    stream=None,
):
    queryset = published_entries().filter(
        class_name=class_name
    )

    if stream:
        queryset = queryset.filter(
            stream=stream
        )

    return queryset


# ============================================================
# TIMETABLE GRID
# ============================================================

def build_grid(entries):
    days = get_days()
    periods = get_teaching_periods()

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
