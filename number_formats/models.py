
from django.db import models


class SchoolNumberSettings(models.Model):
    student_prefix = models.CharField(max_length=30, blank=True, default="STU")
    student_separator = models.CharField(max_length=5, blank=True, default="-")
    student_digits = models.PositiveIntegerField(default=4)
    student_include_year = models.BooleanField(default=False)
    student_year_digits = models.PositiveIntegerField(default=4)
    student_start_number = models.PositiveIntegerField(default=1)

    employee_prefix = models.CharField(max_length=30, blank=True, default="EMP")
    employee_separator = models.CharField(max_length=5, blank=True, default="-")
    employee_digits = models.PositiveIntegerField(default=4)
    employee_include_year = models.BooleanField(default=False)
    employee_year_digits = models.PositiveIntegerField(default=4)
    employee_start_number = models.PositiveIntegerField(default=1)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Number Settings"
        verbose_name_plural = "School Number Settings"

    def __str__(self):
        return "School Number Settings"

    def student_example(self):
        return self._example(
            self.student_prefix,
            self.student_separator,
            self.student_digits,
            self.student_include_year,
            self.student_year_digits,
            self.student_start_number,
        )

    def employee_example(self):
        return self._example(
            self.employee_prefix,
            self.employee_separator,
            self.employee_digits,
            self.employee_include_year,
            self.employee_year_digits,
            self.employee_start_number,
        )

    @staticmethod
    def _example(prefix, separator, digits, include_year, year_digits, number):
        parts = []

        if prefix:
            parts.append(prefix)

        if include_year:
            from django.utils import timezone
            year = str(timezone.localdate().year)
            year = year[-year_digits:]
            parts.append(year)

        parts.append(str(number).zfill(digits))

        return separator.join(parts)
