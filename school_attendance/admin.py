from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "get_class",
        "get_stream",
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

    date_hierarchy = "date"

    list_per_page = 50

    @admin.display(
        description="Class",
        ordering="student__class_name"
    )
    def get_class(self, obj):
        return obj.student.class_name

    @admin.display(
        description="Stream"
    )
    def get_stream(self, obj):

        stream = getattr(
            obj.student,
            "stream",
            ""
        )

        if hasattr(stream, "name"):
            return stream.name

        return stream or ""