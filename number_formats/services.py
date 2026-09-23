
import re

from django.apps import apps
from django.utils import timezone

from .models import SchoolNumberSettings


def get_number_settings():
    settings, _ = SchoolNumberSettings.objects.get_or_create(pk=1)
    return settings


def _year_value(year_digits):
    year = str(timezone.localdate().year)
    try:
        digits = int(year_digits)
    except (TypeError, ValueError):
        digits = 4

    digits = max(1, digits)

    if digits >= len(year):
        return year

    return year[-digits:]


def _format_number(prefix, separator, digits, include_year,
                   year_digits, number):

    prefix = str(prefix or "").strip()
    separator = str(separator or "")

    try:
        digits = int(digits)
    except (TypeError, ValueError):
        digits = 4

    digits = max(1, digits)

    parts = []

    if prefix:
        parts.append(prefix)

    if include_year:
        parts.append(_year_value(year_digits))

    parts.append(str(number).zfill(digits))

    return separator.join(parts)


def _existing_numbers(kind):
    if kind == "student":
        Student = apps.get_model("students", "Student")

        return list(
            Student.objects
            .exclude(admission_no="")
            .values_list("admission_no", flat=True)
        )

    if kind == "employee":
        UserProfile = apps.get_model("accounts", "UserProfile")
        Employee = apps.get_model("hr_payroll", "Employee")

        profile_numbers = list(
            UserProfile.objects
            .exclude(employee_number__isnull=True)
            .exclude(employee_number="")
            .values_list("employee_number", flat=True)
        )

        employee_numbers = list(
            Employee.objects
            .exclude(employee_number__isnull=True)
            .exclude(employee_number="")
            .values_list("employee_number", flat=True)
        )

        return list(set(profile_numbers + employee_numbers))

    return []


def _number_from_value(value, prefix, separator,
                       include_year, year_digits):

    if not value:
        return None

    value = str(value)

    prefix = str(prefix or "").strip()
    separator = str(separator or "")

    if prefix:
        base = re.escape(prefix)
    else:
        base = ""

    if include_year:
        year = _year_value(year_digits)
        year_part = re.escape(separator + year)
    else:
        year_part = ""

    if prefix and separator:
        number_part = re.escape(separator)
    elif prefix:
        number_part = ""
    elif include_year and separator:
        number_part = re.escape(separator)
    else:
        number_part = ""

    pattern = (
        "^"
        + base
        + year_part
        + number_part
        + r"(\d+)"
        + "$"
    )

    match = re.match(pattern, value)

    if not match:
        return None

    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def generate_student_admission_number():
    settings = get_number_settings()

    prefix = settings.student_prefix
    separator = settings.student_separator
    digits = settings.student_digits
    include_year = settings.student_include_year
    year_digits = settings.student_year_digits
    start_number = settings.student_start_number

    existing = _existing_numbers("student")

    highest = 0

    for value in existing:
        number = _number_from_value(
            value,
            prefix,
            separator,
            include_year,
            year_digits,
        )

        if number is not None:
            highest = max(highest, number)

    number = max(int(start_number or 1), highest + 1)

    while True:
        candidate = _format_number(
            prefix,
            separator,
            digits,
            include_year,
            year_digits,
            number,
        )

        if candidate not in existing:
            return candidate

        number += 1


def generate_employee_number():
    settings = get_number_settings()

    prefix = settings.employee_prefix
    separator = settings.employee_separator
    digits = settings.employee_digits
    include_year = settings.employee_include_year
    year_digits = settings.employee_year_digits
    start_number = settings.employee_start_number

    existing = _existing_numbers("employee")

    highest = 0

    for value in existing:
        number = _number_from_value(
            value,
            prefix,
            separator,
            include_year,
            year_digits,
        )

        if number is not None:
            highest = max(highest, number)

    number = max(int(start_number or 1), highest + 1)

    while True:
        candidate = _format_number(
            prefix,
            separator,
            digits,
            include_year,
            year_digits,
            number,
        )

        if candidate not in existing:
            return candidate

        number += 1
