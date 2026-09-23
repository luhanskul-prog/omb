
from django import forms
from .models import SchoolNumberSettings


class SchoolNumberSettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolNumberSettings
        fields = [
            "student_prefix",
            "student_separator",
            "student_digits",
            "student_include_year",
            "student_year_digits",
            "student_start_number",
            "employee_prefix",
            "employee_separator",
            "employee_digits",
            "employee_include_year",
            "employee_year_digits",
            "employee_start_number",
        ]

        widgets = {
            "student_include_year": forms.CheckboxInput(),
            "employee_include_year": forms.CheckboxInput(),
        }
