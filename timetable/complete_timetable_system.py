from django.utils import timezone
from django.db.models import Q

from .models import (
    TimetableLesson,
    TimetableTeacher,
    TimetableClass,
    TimetablePeriod,
    TimetableDay,
    TimetableTerm,
)

from .advanced_models import TimetableVersion

from .legacy_compat import resolve_teacher


def current_draft(term=None):
    qs = (
        TimetableVersion.objects
        .filter(
            status="DRAFT"
        )
    )

    if term is not None:
        qs = qs.filter(
            term=term
        )

    return (
        qs
        .order_by(
            "-created_at",
            "-id",
        )
        .first()
    )


def published_version():
    return (
        TimetableVersion.objects
        .filter(status="PUBLISHED")
        .order_by("-published_at", "-created_at", "-id")
        .first()
    )


def published_entries(term=None):
    qs = (
        TimetableLesson.objects
        .filter(
            is_active=True,
            is_published=True,
        )
        .select_related(
            "term",
            "class_group",
            "subject",
            "teacher",
            "room",
            "day",
            "period",
        )
        .order_by(
            "day__order",
            "period__order",
            "class_group__name",
        )
    )

    if term is not None:
        qs = qs.filter(
            term=term
        )

    version = published_version()

    if version:
        return qs.filter(
            version=version
        )

    return qs


def teacher_entries(teacher, term=None):
    target = resolve_teacher(teacher)

    if not target:
        return TimetableLesson.objects.none()

    return published_entries(term).filter(
        teacher=target
    )


def class_entries(class_name, stream=None, term=None):
    qs = published_entries(term).filter(
        class_group__name=class_name
    )

    if stream not in (None, ""):
        qs = qs.filter(
            Q(class_group__stream=stream)
            | Q(class_group__stream__isnull=True)
            | Q(class_group__stream="")
        )

    return qs


def get_days():
    return TimetableDay.objects.filter(
        active=True
    ).order_by("order", "id")


def get_periods():
    return (
        TimetablePeriod.objects
        .filter(
            active=True,
            is_break=False,
            is_lunch=False,
            is_activity=False,
        )
        .order_by("order", "id")
    )


def teaching_periods():
    return get_periods()


def check_timetable(term=None):
    lessons = published_entries(term)

    conflicts = []

    class_seen = {}
    teacher_seen = {}
    room_seen = {}

    for lesson in lessons:

        key = (
            lesson.class_group_id,
            lesson.day_id,
            lesson.period_id,
        )

        if key in class_seen:
            conflicts.append(
                {
                    "type": "class",
                    "lesson": lesson.id,
                    "with": class_seen[key],
                }
            )

        class_seen[key] = lesson.id

        if lesson.teacher_id:
            key = (
                lesson.teacher_id,
                lesson.day_id,
                lesson.period_id,
            )

            if key in teacher_seen:
                conflicts.append(
                    {
                        "type": "teacher",
                        "lesson": lesson.id,
                        "with": teacher_seen[key],
                    }
                )

            teacher_seen[key] = lesson.id

        if lesson.room_id:
            key = (
                lesson.room_id,
                lesson.day_id,
                lesson.period_id,
            )

            if key in room_seen:
                conflicts.append(
                    {
                        "type": "room",
                        "lesson": lesson.id,
                        "with": room_seen[key],
                    }
                )

            room_seen[key] = lesson.id

    return {
        "ok": not conflicts,
        "conflicts": conflicts,
        "count": len(conflicts),
    }


def unpublish(term=None):
    version = published_version()

    if term is not None:
        if (
            not version
            or version.term_id != term.id
        ):
            return None

    if not version:
        return None

    TimetableLesson.objects.filter(
        version=version,
        is_active=True,
    ).update(
        is_published=False,
    )

    version.status = "DRAFT"
    version.published_at = None
    version.archived_at = None

    version.save(
        update_fields=[
            "status",
            "published_at",
            "archived_at",
        ]
    )

    return version


def publish_draft(term=None):
    draft = current_draft(
        term
    )

    if not draft:
        return None

    result = check_timetable(
        draft.term
    )

    if not result["ok"]:
        return result

    now = timezone.now()

    previous_versions = (
        TimetableVersion.objects
        .filter(
            status="PUBLISHED"
        )
        .exclude(
            pk=draft.pk
        )
    )

    for previous in previous_versions:

        TimetableLesson.objects.filter(
            version=previous,
            is_active=True,
        ).update(
            is_published=False,
        )

        previous.status = "ARCHIVED"
        previous.archived_at = now

        previous.save(
            update_fields=[
                "status",
                "archived_at",
            ]
        )

    TimetableLesson.objects.filter(
        is_active=True,
        is_published=True,
    ).exclude(
        version=draft,
    ).update(
        is_published=False,
    )

    TimetableLesson.objects.filter(
        version=draft,
        is_active=True,
    ).update(
        is_published=True,
    )

    draft.status = "PUBLISHED"
    draft.published_at = now
    draft.archived_at = None

    draft.save(
        update_fields=[
            "status",
            "published_at",
            "archived_at",
        ]
    )

    return draft


def build_assignment_requirements():
    try:
        from .advanced_models import TimetableTeacherTeachingAssignment
        return TimetableTeacherTeachingAssignment.objects.filter(
            is_active=True
        )
    except Exception:
        return []


def grid(term=None, class_name=None, stream=None):
    qs = published_entries(term)

    if class_name:
        qs = qs.filter(
            class_group__name=class_name
        )

    if stream:
        qs = qs.filter(
            class_group__stream=stream
        )

    result = {}

    for lesson in qs:
        result.setdefault(
            lesson.day_id,
            {}
        ).setdefault(
            lesson.period_id,
            []
        ).append(lesson)

    return result
