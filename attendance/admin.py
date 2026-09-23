from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "date",
        "status",
        "remarks",
    )

    list_filter = (
        "date",
        "status",
    )

    search_fields = (
        "student__first_name",
        "student__middle_name",
        "student__last_name",
        "student__admission_no",
    )

    ordering = (
        "-date",
        "student__first_name",
    )