from django.contrib import admin

from .models import WeeklyAssessmentReport, WeeklyReportReply


@admin.register(WeeklyAssessmentReport)
class WeeklyAssessmentReportAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "subject",
        "class_name",
        "stream",
        "week_number",
        "week_start",
        "week_end",
        "score",
        "max_score",
        "is_published",
        "created_by",
        "created_at",
    )

    list_filter = (
        "is_published",
        "week_number",
        "week_start",
        "week_end",
        "subject",
        "class_name",
    )

    search_fields = (
        "student__first_name",
        "student__middle_name",
        "student__last_name",
        "student__admission_no",
        "teacher_report",
    )

    autocomplete_fields = (
        "student",
        "created_by",
        "updated_by",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-week_start",
        "student__last_name",
        "student__first_name",
        "subject__name",
    )


@admin.register(WeeklyReportReply)
class WeeklyReportReplyAdmin(admin.ModelAdmin):
    list_display = (
        "report",
        "author",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "message",
        "author__username",
        "author__first_name",
        "author__last_name",
        "report__student__first_name",
        "report__student__last_name",
        "report__student__admission_no",
    )

    autocomplete_fields = (
        "report",
        "author",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


from .models import WeeklyAssessmentWeek

@admin.register(WeeklyAssessmentWeek)
class WeeklyAssessmentWeekAdmin(admin.ModelAdmin):
    list_display = (
        "week_number",
        "title",
        "academic_year",
        "term",
        "week_start",
        "week_end",
        "is_locked",
        "created_at",
    )
    list_filter = ("academic_year", "term", "is_locked")
    search_fields = ("title",)
