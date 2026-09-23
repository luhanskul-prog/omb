from django.db.models import Q

from .models import (
    TimetableSubject,
    TimetableTeacher,
    TimetableRoom,
    TimetablePeriod,
    TimetableDay,
    TimetableLesson,
    TimetableTerm,
)

from .advanced_models import (
    TimetableTeacherClassAssignment,
    TimetableTeacherTeachingAssignment,
    TimetableTeacherSubject,
    TimetableConfiguration,
    TimetableConfiguredSlot,
    TimetableSlotRule,
    TimetableAssignmentGroup,
    TimetableAssignmentMember,
    TimetableExamSchedule,
    TimetableTeacherSubstitution,
)


# ----------------------------------------------------------
# Compatibility field aliases
# ----------------------------------------------------------

if not hasattr(TimetableSubject, "is_active"):
    TimetableSubject.is_active = property(
        lambda self: self.active,
        lambda self, value: setattr(self, "active", value),
    )

if not hasattr(TimetableTeacher, "is_active"):
    TimetableTeacher.is_active = property(
        lambda self: self.active,
        lambda self, value: setattr(self, "active", value),
    )

if not hasattr(TimetableTeacher, "employee_no"):
    TimetableTeacher.employee_no = property(
        lambda self: self.staff_number,
        lambda self, value: setattr(self, "staff_number", value),
    )

if not hasattr(TimetableRoom, "is_active"):
    TimetableRoom.is_active = property(
        lambda self: self.active,
        lambda self, value: setattr(self, "active", value),
    )

if not hasattr(TimetableLesson, "class_name"):
    TimetableLesson.class_name = property(
        lambda self: self.class_group.name
        if self.class_group_id else "",
    )

if not hasattr(TimetableLesson, "stream"):
    TimetableLesson.stream = property(
        lambda self: self.class_group.stream
        if self.class_group_id else "",
    )

if not hasattr(TimetableLesson, "is_fixed"):
    TimetableLesson.is_fixed = property(
        lambda self: self.locked,
        lambda self, value: setattr(self, "locked", value),
    )


# ----------------------------------------------------------
# Small queryset facade translating legacy field names
# ----------------------------------------------------------

class CompatManager:

    def __init__(self, model, field_map=None):
        self.model = model
        self.field_map = field_map or {}

    def _translate_key(self, key):
        pieces = key.split("__", 1)
        base = pieces[0]

        if base in self.field_map:
            if len(pieces) == 1:
                return self.field_map[base]

            return (
                self.field_map[base]
                + "__"
                + pieces[1]
            )

        return key

    def _translate_kwargs(self, kwargs):
        return {
            self._translate_key(k): v
            for k, v in kwargs.items()
        }

    def all(self):
        return self.model.objects.all()

    def filter(self, *args, **kwargs):
        return self.model.objects.filter(
            *args,
            **self._translate_kwargs(kwargs),
        )

    def exclude(self, *args, **kwargs):
        return self.model.objects.exclude(
            *args,
            **self._translate_kwargs(kwargs),
        )

    def get(self, *args, **kwargs):
        return self.model.objects.get(
            *args,
            **self._translate_kwargs(kwargs),
        )

    def create(self, **kwargs):
        return self.model.objects.create(
            **self._translate_kwargs(kwargs)
        )

    def get_or_create(self, defaults=None, **kwargs):
        translated = self._translate_kwargs(kwargs)

        if defaults:
            defaults = self._translate_kwargs(defaults)

        return self.model.objects.get_or_create(
            defaults=defaults,
            **translated,
        )

    def update_or_create(self, defaults=None, **kwargs):
        translated = self._translate_kwargs(kwargs)

        if defaults:
            defaults = self._translate_kwargs(defaults)

        return self.model.objects.update_or_create(
            defaults=defaults,
            **translated,
        )

    def __getattr__(self, name):
        return getattr(self.model.objects, name)


class Subject:
    objects = CompatManager(
        TimetableSubject,
        {
            "is_active": "active",
        },
    )

    DoesNotExist = TimetableSubject.DoesNotExist
    MultipleObjectsReturned = TimetableSubject.MultipleObjectsReturned


class Teacher:
    objects = CompatManager(
        TimetableTeacher,
        {
            "is_active": "active",
            "employee_no": "staff_number",
        },
    )

    DoesNotExist = TimetableTeacher.DoesNotExist
    MultipleObjectsReturned = TimetableTeacher.MultipleObjectsReturned


class Room:
    objects = CompatManager(
        TimetableRoom,
        {
            "is_active": "active",
        },
    )

    DoesNotExist = TimetableRoom.DoesNotExist
    MultipleObjectsReturned = TimetableRoom.MultipleObjectsReturned


class TimetableEntry:
    objects = CompatManager(
        TimetableLesson,
        {
            "class_name": "class_group__name",
            "stream": "class_group__stream",
            "is_fixed": "locked",
        },
    )

    DoesNotExist = TimetableLesson.DoesNotExist
    MultipleObjectsReturned = TimetableLesson.MultipleObjectsReturned


# ----------------------------------------------------------
# Canonical model aliases
# ----------------------------------------------------------

TeacherClassAssignment = TimetableTeacherClassAssignment
TeacherTeachingAssignment = TimetableTeacherTeachingAssignment
TeacherSubject = TimetableTeacherSubject

Period = TimetablePeriod
Day = TimetableDay

ExamSchedule = TimetableExamSchedule
TeacherSubstitution = TimetableTeacherSubstitution


# ----------------------------------------------------------
# Helper
# ----------------------------------------------------------

def resolve_teacher(value):
    if value is None:
        return None

    if isinstance(value, TimetableTeacher):
        return value

    employee_id = getattr(value, "employee_id", None)

    if employee_id:
        teacher = TimetableTeacher.objects.filter(
            employee_id=employee_id
        ).first()

        if teacher:
            return teacher

    employee_no = getattr(
        value,
        "employee_no",
        None,
    )

    if employee_no:
        teacher = TimetableTeacher.objects.filter(
            staff_number=employee_no
        ).first()

        if teacher:
            return teacher

    if isinstance(value, int):
        return TimetableTeacher.objects.filter(
            pk=value
        ).first()

    name = getattr(value, "name", None)

    if name:
        return TimetableTeacher.objects.filter(
            name__iexact=name
        ).first()

    return None


