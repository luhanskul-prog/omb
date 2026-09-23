from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "admission_no",
        "first_name",
        "middle_name",
        "last_name",
        "gender",
        "class_name",
        "date_admitted",
    )

    search_fields = (
        "admission_no",
        "first_name",
        "middle_name",
        "last_name",
    )

    list_filter = (
        "gender",
        "class_name",
    )