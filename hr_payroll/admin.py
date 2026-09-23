from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        "employee_number",
        "first_name",
        "middle_name",
        "last_name",
        "position",
        "department",
        "employment_status",
        "is_active",
    )

    search_fields = (
        "employee_number",
        "first_name",
        "middle_name",
        "last_name",
    )

    list_filter = (
        "employment_status",
        "is_active",
        "department",
        "position",
    )
