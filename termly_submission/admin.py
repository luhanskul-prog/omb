
from django.contrib import admin

from .models import TermlySubmissionRequirement


@admin.register(TermlySubmissionRequirement)
class TermlySubmissionRequirementAdmin(admin.ModelAdmin):

    list_display = (
        "teacher",
        "academic_year",
        "term",
        "class_name",
        "stream",
        "subject",
        "expected_schemes",
        "expected_records",
        "expected_lesson_plans",
    )

    list_filter = (
        "academic_year",
        "term",
        "subject",
        "class_name",
    )

    search_fields = (
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
        "class_name",
        "stream",
        "subject__name",
    )
