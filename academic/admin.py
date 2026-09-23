from django.contrib import admin

from .models import (
    Stream,
    Subject,
    AssessmentType,
    GradingScale,
    Assessment,
)


# ============================================================
# STREAM
# ============================================================

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )


# ============================================================
# SUBJECT
# ============================================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )


# ============================================================
# ASSESSMENT TYPE
# ============================================================

@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "code",
        "order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "order",
        "name",
    )


# ============================================================
# GRADING SCALE
# ============================================================

@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):

    list_display = (
        "grade",
        "minimum_score",
        "maximum_score",
        "points",
        "is_active",
    )

    list_filter = (
        "is_active",
        "grade",
    )

    search_fields = (
        "grade",
    )

    list_editable = (
        "minimum_score",
        "maximum_score",
        "points",
        "is_active",
    )

    ordering = (
        "-minimum_score",
    )


# ============================================================
# ASSESSMENT / MARKS
# ============================================================

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "subject",
        "assessment_type",
        "academic_year",
        "term",
        "score",
        "get_grade",
        "get_points",
    )

    list_filter = (
        "academic_year",
        "term",
        "assessment_type",
        "subject",
    )

    search_fields = (
        "student__first_name",
        "student__middle_name",
        "student__last_name",
        "student__admission_no",
        "subject__name",
        "subject__code",
        "assessment_type__name",
        "assessment_type__code",
    )

    list_editable = (
        "score",
    )

    autocomplete_fields = (
        "student",
        "subject",
        "assessment_type",
        "academic_year",
        "term",
    )

    ordering = (
        "student",
        "subject",
        "assessment_type",
    )

    # --------------------------------------------------------
    # GRADE
    # --------------------------------------------------------

    @admin.display(
        description="Grade",
        ordering="score"
    )
    def get_grade(self, obj):

        return obj.grade()

    # --------------------------------------------------------
    # POINTS
    # --------------------------------------------------------

    @admin.display(
        description="Points",
        ordering="score"
    )
    def get_points(self, obj):

        return obj.points()