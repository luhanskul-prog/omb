from django.contrib import admin

from .models import (
    TimetablePeriod,
    TimetableDay,
    TimetableTerm,
    TimetableClass,
    TimetableSubject,
    TimetableTeacher,
    TimetableRoom,
    LessonRequirement,
    TeacherAvailability,
    TimetableLesson,
    TimetableConstraint,
)


@admin.register(TimetablePeriod)
class TimetablePeriodAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "start_time",
        "end_time",
        "order",
        "is_break",
        "is_lunch",
        "is_activity",
        "active",
    )
    list_filter = ("is_break", "is_lunch", "is_activity", "active")


@admin.register(TimetableDay)
class TimetableDayAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "order", "active")
    list_filter = ("active",)


@admin.register(TimetableTerm)
class TimetableTermAdmin(admin.ModelAdmin):
    list_display = (
        "academic_year",
        "term_name",
        "start_date",
        "end_date",
        "active",
    )
    list_filter = ("academic_year", "term_name", "active")


@admin.register(TimetableClass)
class TimetableClassAdmin(admin.ModelAdmin):
    list_display = ("name", "stream", "level", "active")
    list_filter = ("level", "active")
    search_fields = ("name", "stream")


@admin.register(TimetableSubject)
class TimetableSubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active")
    list_filter = ("active",)
    search_fields = ("name", "code")


@admin.register(TimetableTeacher)
class TimetableTeacherAdmin(admin.ModelAdmin):
    list_display = ("name", "staff_number", "email", "active")
    list_filter = ("active",)
    search_fields = ("name", "staff_number", "email")
    filter_horizontal = ("subjects",)


@admin.register(TimetableRoom)
class TimetableRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_type", "capacity", "active")
    list_filter = ("room_type", "active")
    search_fields = ("name",)


@admin.register(LessonRequirement)
class LessonRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "class_group",
        "subject",
        "teacher",
        "room",
        "lessons_per_week",
        "duration_periods",
        "requires_double",
        "double_lessons_per_week",
        "practical",
        "active",
    )
    list_filter = ("requires_double", "practical", "active")
    search_fields = ("class_group__name", "subject__name")


@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("teacher", "day", "period", "available")
    list_filter = ("available", "day")


@admin.register(TimetableLesson)
class TimetableLessonAdmin(admin.ModelAdmin):
    list_display = (
        "term",
        "class_group",
        "subject",
        "teacher",
        "room",
        "day",
        "period",
        "duration_periods",
        "locked",
    )
    list_filter = ("term", "day", "locked")
    search_fields = (
        "class_group__name",
        "subject__name",
        "teacher__name",
    )


@admin.register(TimetableConstraint)
class TimetableConstraintAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "constraint_type",
        "hard_constraint",
        "weight",
        "active",
    )
    list_filter = (
        "constraint_type",
        "hard_constraint",
        "active",
    )
