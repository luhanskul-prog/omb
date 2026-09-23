from .advanced_models import TimetableVersion
from django.utils import timezone
import random

from collections import defaultdict

from django.db import transaction

from .models import (
    TimetableTerm,
    TimetableDay,
    TimetablePeriod,
    TimetableLesson,
    LessonRequirement,
    TeacherAvailability,
)


class TimetableGenerator:
    """
    Constraint-aware timetable generator.

    Priority:
        100 = highest
        1   = lowest

    Hard constraints:
        - Class cannot have two lessons at the same time
        - Teacher cannot teach two lessons at the same time
        - Room cannot host two lessons at the same time
        - Teacher availability is respected
        - Break/lunch/activity periods are excluded
        - Locked lessons are preserved
        - Multi-period lessons require consecutive usable periods
    """

    def __init__(self, term, version=None):
        self.term = term
        self.version = version

        self.days = list(
            TimetableDay.objects.filter(
                active=True
            ).order_by("order")
        )

        self.periods = list(
            TimetablePeriod.objects.filter(
                active=True,
                is_break=False,
                is_lunch=False,
                is_activity=False,
            ).order_by("order")
        )

        self.requirements = list(
            LessonRequirement.objects.filter(
                active=True
            )
            .select_related(
                "class_group",
                "subject",
                "teacher",
                "room",
                "preferred_day",
            )
            .order_by(
                "-priority",
                "-requires_double",
                "-practical",
                "-duration_periods",
                "-lessons_per_week",
                "class_group__name",
                "subject__name",
            )
        )

        self.locked_lessons = list(
            TimetableLesson.objects.filter(
                term=term,
                locked=True,
                is_active=True,
            ).select_related(
                "class_group",
                "teacher",
                "room",
                "day",
                "period",
            )
        )

        self.class_busy = set()
        self.teacher_busy = set()
        self.room_busy = set()

        self.created = 0
        self.failed = []

        self._load_locked_lessons()

    # ---------------------------------------------------------
    # LOCKED LESSONS
    # ---------------------------------------------------------

    def _load_locked_lessons(self):
        for lesson in self.locked_lessons:
            start_index = next(
                (i for i, p in enumerate(self.periods) if p.id == lesson.period_id),
                None,
            )

            if start_index is None:
                continue

            periods = self._period_block(
                start_index,
                lesson.duration_periods,
            )

            if not periods:
                periods = [self.periods[start_index]]

            for period in periods:
                key = (lesson.day_id, period.id)

                self.class_busy.add(
                    (lesson.class_group_id, *key)
                )

                if lesson.teacher_id:
                    self.teacher_busy.add(
                        (lesson.teacher_id, *key)
                    )

                if lesson.room_id:
                    self.room_busy.add(
                        (lesson.room_id, *key)
                    )

    # ---------------------------------------------------------
    # PERIOD BLOCKS
    # ---------------------------------------------------------

    def _period_block(self, start_index, duration):
        """
        Return consecutive period objects.
        """
        if start_index + duration > len(self.periods):
            return None

        block = self.periods[
            start_index:start_index + duration
        ]

        # Must be genuinely consecutive in configured order.
        for i in range(len(block) - 1):
            if block[i + 1].order != block[i].order + 1:
                return None

        return block

    # ---------------------------------------------------------
    # AVAILABILITY
    # ---------------------------------------------------------

    def _teacher_available(self, teacher_id, day_id, periods):
        if not teacher_id:
            return True

        unavailable = set(
            TeacherAvailability.objects.filter(
                teacher_id=teacher_id,
                day_id=day_id,
                period_id__in=[p.id for p in periods],
                available=False,
            ).values_list("period_id", flat=True)
        )

        return not any(p.id in unavailable for p in periods)

    # ---------------------------------------------------------
    # CONFLICT CHECK
    # ---------------------------------------------------------

    def _free(self, requirement, day, periods):
        class_id = requirement.class_group_id
        teacher_id = requirement.teacher_id
        room_id = requirement.room_id

        for period in periods:
            key = (day.id, period.id)

            if (class_id, *key) in self.class_busy:
                return False

            if teacher_id and (teacher_id, *key) in self.teacher_busy:
                return False

            if room_id and (room_id, *key) in self.room_busy:
                return False

        if not self._teacher_available(
            teacher_id,
            day.id,
            periods,
        ):
            return False

        return True

    # ---------------------------------------------------------
    # SCORE A SLOT
    # ---------------------------------------------------------

    def _score(self, requirement, day, start_index):
        score = 0

        # Priority is the strongest factor.
        score += requirement.priority * 100

        # Preferred day gets a major bonus.
        if requirement.preferred_day_id:
            if day.id == requirement.preferred_day_id:
                score += 5000

        # Practical lessons are slightly preferred earlier.
        if requirement.practical:
            if start_index <= max(1, len(self.periods) // 2):
                score += 250

        # Double lessons benefit from earlier uninterrupted space.
        if requirement.requires_double or requirement.duration_periods > 1:
            score += max(0, 100 - start_index)

        # Avoid stacking same subject repeatedly on same day.
        existing_same_day = TimetableLesson.objects.filter(
            term=self.term,
            class_group=requirement.class_group,
            subject=requirement.subject,
            day=day,
        ).count()

        score -= existing_same_day * 300

        # Spread lessons across the week.
        existing_subject_days = set(
            TimetableLesson.objects.filter(
                term=self.term,
                class_group=requirement.class_group,
                subject=requirement.subject,
            ).values_list("day_id", flat=True)
        )

        if day.id not in existing_subject_days:
            score += 400

        return score

    # ---------------------------------------------------------
    # FIND BEST SLOT
    # ---------------------------------------------------------

    def _find_slot(self, requirement):
        """
        Find a valid timetable slot.

        HARD COLLISION RULES are enforced by _free():
            - teacher cannot teach two classes at the same time
            - class cannot have two subjects at the same time
            - room cannot host two lessons at the same time
            - teacher availability is respected

        The generator searches Monday-Friday in randomized order.
        Only conflict-free slots enter the candidate list.
        """

        candidates = []

        days = list(self.days)

        # Randomize Monday-Friday so generation does not always
        # fill the timetable in the same order.
        random.shuffle(days)

        # Preferred day remains available as a priority.
        if requirement.preferred_day_id:
            preferred = [
                d for d in days
                if d.id == requirement.preferred_day_id
            ]
            others = [
                d for d in days
                if d.id != requirement.preferred_day_id
            ]

            # Keep preferred day first, but randomize the rest.
            random.shuffle(others)
            days = preferred + others

        period_indexes = list(range(len(self.periods)))
        random.shuffle(period_indexes)

        for day in days:
            for start_index in period_indexes:

                block = self._period_block(
                    start_index,
                    requirement.duration_periods,
                )

                if not block:
                    continue

                # HARD CONFLICT CHECK.
                # Nothing is added to candidates unless ALL
                # teacher/class/room constraints are satisfied.
                if not self._free(
                    requirement,
                    day,
                    block,
                ):
                    continue

                score = self._score(
                    requirement,
                    day,
                    start_index,
                )

                # Small random tie-breaker prevents identical
                # schedules on repeated generations while the
                # scoring system still controls placement.
                candidates.append(
                    (
                        score,
                        random.random(),
                        day,
                        block,
                    )
                )

        if not candidates:
            return None

        # Highest score first.
        # Random value only breaks ties between otherwise
        # similarly scored valid choices.
        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            ),
            reverse=True,
        )

        return candidates[0][2], candidates[0][3]

    # ---------------------------------------------------------
    # MARK BUSY
    # ---------------------------------------------------------

    def _mark_busy(self, lesson, periods):
        for period in periods:
            key = (lesson.day_id, period.id)

            self.class_busy.add(
                (lesson.class_group_id, *key)
            )

            if lesson.teacher_id:
                self.teacher_busy.add(
                    (lesson.teacher_id, *key)
                )

            if lesson.room_id:
                self.room_busy.add(
                    (lesson.room_id, *key)
                )

    # ---------------------------------------------------------
    # CREATE LESSON
    # ---------------------------------------------------------

    def _create_lesson(self, requirement, day, periods):
        first_period = periods[0]

        lesson = TimetableLesson.objects.create(
            term=self.term,
            version=self.version,
            class_group=requirement.class_group,
            subject=requirement.subject,
            teacher=requirement.teacher,
            room=requirement.room,
            day=day,
            period=first_period,
            duration_periods=len(periods),
            locked=False,
            is_published=False,
            is_active=True,
            notes=requirement.notes,
        )

        self._mark_busy(
            lesson,
            periods,
        )

        self.created += 1

    # ---------------------------------------------------------
    # GENERATE
    # ---------------------------------------------------------

    @transaction.atomic
    def _lesson_pattern(self, requirement):
        """
        Build the weekly occurrence pattern.

        Example:
            6 lessons + 2 doubles
            -> [2, 2, 1, 1, 1, 1]

            5 lessons + 2 doubles
            -> [2, 2, 1, 1, 1]

            4 lessons + 1 double
            -> [2, 1, 1, 1]
        """
        total = int(requirement.lessons_per_week or 0)
        doubles = int(
            getattr(requirement, "double_lessons_per_week", 0) or 0
        )

        # Backwards compatibility with the old checkbox.
        if doubles == 0 and getattr(requirement, "requires_double", False):
            doubles = 1

        if total <= 0:
            return []

        # A double consumes two periods but remains ONE lesson occurrence.
        max_doubles = total
        doubles = min(doubles, max_doubles)

        # Never allow an impossible pattern.
        if doubles * 2 > total * 2:
            doubles = total

        singles = total - doubles

        pattern = [2] * doubles + [1] * singles

        # Put doubles first so the placement algorithm can find
        # contiguous periods before filling single lessons.
        return pattern

    @transaction.atomic
    def generate(self):
        # Remove old draft lessons for this term only.
        old_drafts = list(
            TimetableVersion.objects.filter(
                term=self.term,
                status=TimetableVersion.STATUS_DRAFT,
            )
        )

        old_draft_ids = [
            draft.id
            for draft in old_drafts
        ]

        if old_draft_ids:

            TimetableLesson.objects.filter(
                version_id__in=old_draft_ids,
                locked=False,
                is_published=False,
            ).delete()

            for old_draft in old_drafts:

                if not TimetableLesson.objects.filter(
                    version=old_draft
                ).exists():

                    old_draft.delete()

        # Remove only unversioned generated lessons.
        # Published/versioned timetable data is protected.
        TimetableLesson.objects.filter(
            term=self.term,
            version__isnull=True,
            locked=False,
            is_published=False,
        ).delete()

        timestamp = timezone.localtime().strftime(
            "%Y-%m-%d %H:%M"
        )

        self.version = TimetableVersion.objects.create(
            term=self.term,
            name=(
                f"Timetable Draft - "
                f"{self.term.academic_year} - "
                f"{self.term.term_name} - "
                f"{timestamp}"
            ),
            status=TimetableVersion.STATUS_DRAFT,
        )

        self.class_busy.clear()
        self.teacher_busy.clear()
        self.room_busy.clear()
        self.created = 0
        self.failed = []

        self._load_locked_lessons()

        randomized_requirements = list(
            self.requirements
        )

        random.shuffle(
            randomized_requirements
        )

        for requirement in randomized_requirements:

            pattern = self._lesson_pattern(
                requirement
            )

            for occurrence, duration in enumerate(
                pattern
            ):

                original_duration = (
                    requirement.duration_periods
                )

                requirement.duration_periods = (
                    duration
                )

                slot = self._find_slot(
                    requirement
                )

                requirement.duration_periods = (
                    original_duration
                )

                if slot:

                    day, periods = slot

                    self._create_lesson(
                        requirement,
                        day,
                        periods,
                    )

                else:

                    self.failed.append(
                        {
                            "class_group": str(
                                requirement.class_group
                            ),
                            "subject": str(
                                requirement.subject
                            ),
                            "teacher": (
                                str(requirement.teacher)
                                if requirement.teacher
                                else "Not assigned"
                            ),
                            "priority": requirement.priority,
                            "duration": duration,
                            "occurrence": occurrence + 1,
                            "lesson_type": (
                                "DOUBLE"
                                if duration == 2
                                else "SINGLE"
                            ),
                            "reason": (
                                "No conflict-free slot was available."
                            ),
                        }
                    )

        return {
            "created": self.created,
            "failed": self.failed,
            "requested": sum(
                r.lessons_per_week
                for r in self.requirements
            ),
            "locked": len(
                self.locked_lessons
            ),
            "term": self.term,
            "version": self.version,
            "version_id": self.version.id,
            "version_name": self.version.name,
        }


def generate_timetable(term=None):
    if term is None:
        term = (
            TimetableTerm.objects
            .filter(active=True)
            .order_by("-id")
            .first()
        )

    if not term:
        return {
            "created": 0,
            "failed": [],
            "requested": 0,
            "locked": 0,
            "error": "No active timetable term exists.",
        }

    generator = TimetableGenerator(term)

    result = generator.generate()

    result["term"] = term

    return result
