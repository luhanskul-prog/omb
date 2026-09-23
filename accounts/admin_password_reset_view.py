from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string

from students.models import Student
from hr_payroll.models import Employee
from .views import admin_required


@login_required
def admin_password_reset(request):
    if not admin_required(request):
        messages.error(
            request,
            "You do not have permission to reset user passwords."
        )
        return redirect("accounts:admin_dashboard")

    generated_password = None
    reset_username = None
    reset_account_type = None

    if request.method == "POST":
        identifier_type = (
            request.POST.get("identifier_type") or ""
        ).strip()
        identifier = (
            request.POST.get("identifier") or ""
        ).strip()

        if not identifier:
            messages.error(
                request,
                "Please enter the required account identifier."
            )
            return render(
                request,
                "accounts/admin_password_reset.html"
            )

        User = get_user_model()
        user = None

        if identifier_type == "student":
            student = Student.objects.filter(
                admission_no__iexact=identifier
            ).first()

            if not student:
                messages.error(
                    request,
                    f"No student was found with admission number "
                    f"'{identifier}'."
                )
            else:
                try:
                    user = student.user_account.user
                except Exception:
                    user = None

                if user is None:
                    user = User.objects.filter(
                        profile__student=student,
                        profile__role="STUDENT"
                    ).first()

                if user is None:
                    messages.error(
                        request,
                        f"The student '{student.get_full_name()}' "
                        f"does not have a login account."
                    )
                else:
                    reset_account_type = "Student"

        elif identifier_type == "staff":
            employee = Employee.objects.filter(
                employee_number__iexact=identifier
            ).first()

            if not employee:
                messages.error(
                    request,
                    f"No staff member was found with employee number "
                    f"'{identifier}'."
                )
            else:
                user = User.objects.filter(
                    profile__employee=employee
                ).first()

                if user is None:
                    messages.error(
                        request,
                        f"The staff member with employee number "
                        f"'{identifier}' does not have a login account."
                    )
                else:
                    reset_account_type = "Staff"

        elif identifier_type == "parent":
            user = User.objects.filter(
                username__iexact=identifier,
                parent__isnull=False
            ).first()

            if user is None:
                messages.error(
                    request,
                    f"No parent account was found with username "
                    f"'{identifier}'."
                )
            else:
                reset_account_type = "Parent"

        else:
            messages.error(
                request,
                "Please select a valid account type."
            )

        if user is not None:
            generated_password = (
                get_random_string(
                    4,
                    allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ"
                )
                + get_random_string(
                    4,
                    allowed_chars="abcdefghijkmnopqrstuvwxyz"
                )
                + get_random_string(
                    2,
                    allowed_chars="23456789"
                )
                + get_random_string(
                    2,
                    allowed_chars="!@#$%"
                )
            )

            user.set_password(generated_password)
            user.save(update_fields=["password"])

            reset_username = user.username

            messages.success(
                request,
                f"{reset_account_type} password reset successfully."
            )

    return render(
        request,
        "accounts/admin_password_reset.html",
        {
            "generated_password": generated_password,
            "reset_username": reset_username,
            "reset_account_type": reset_account_type,
        },
    )
