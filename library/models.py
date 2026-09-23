from datetime import date
import re
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Book(models.Model):
    STATUS_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
    ]

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150)
    isbn = models.CharField(max_length=20, blank=True)
    publisher = models.CharField(max_length=150, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )

    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    shelf_number = models.CharField(max_length=50, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )

    description = models.TextField(blank=True)

    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def update_status(self):
        if self.available_copies > 0:
            self.status = "available"
        else:
            self.status = "unavailable"

        self.save(update_fields=["status"])

    def save(self, *args, **kwargs):
        """
        Automatically generate a unique Library ISBN.

        Format:
            LIB-0001-2026
            LIB-0002-2026

        The sequence automatically starts from 0001
        when a new calendar year begins.
        Existing ISBN values are never replaced.
        """

        if not self.isbn:
            current_year = date.today().year
            prefix = f"LIB-"
            suffix = f"-{current_year}"

            BookModel = type(self)

            existing_numbers = []

            for existing in BookModel.objects.exclude(
                isbn__isnull=True
            ).exclude(
                isbn=""
            ).values_list("isbn", flat=True):

                match = re.fullmatch(
                    rf"LIB-(\d+)-{current_year}",
                    str(existing).strip()
                )

                if match:
                    existing_numbers.append(
                        int(match.group(1))
                    )

            next_number = (
                max(existing_numbers) + 1
                if existing_numbers
                else 1
            )

            candidate = (
                f"{prefix}{next_number:04d}{suffix}"
            )

            # Absolute uniqueness protection.
            while BookModel.objects.filter(
                isbn=candidate
            ).exists():

                next_number += 1

                candidate = (
                    f"{prefix}{next_number:04d}{suffix}"
                )

            self.isbn = candidate

        super().save(*args, **kwargs)


class LibraryMember(models.Model):
    MEMBER_TYPES = [
        ("student", "Student"),
        ("staff", "Staff"),
    ]

    name = models.CharField(max_length=150)

    admission_number = models.CharField(
        max_length=50,
        blank=True,
    )

    member_type = models.CharField(
        max_length=20,
        choices=MEMBER_TYPES,
        default="student",
    )

    student = models.OneToOneField(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_member",
    )

    employee = models.OneToOneField(
        "hr_payroll.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_member",
    )

    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    active = models.BooleanField(default=True)

    date_registered = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        if self.member_type == "student" and self.student:
            return (
                f"{self.student.admission_no} - "
                f"{self.student.first_name} "
                f"{self.student.last_name}"
            )

        if self.member_type == "staff" and self.employee:
            return (
                f"{self.employee.employee_number} - "
                f"{self.employee.first_name} "
                f"{self.employee.last_name}"
            )

        return self.name


class BookIssue(models.Model):
    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("returned", "Returned"),
        ("overdue", "Overdue"),
    ]

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    member = models.ForeignKey(
        LibraryMember,
        on_delete=models.CASCADE,
        related_name="book_issues",
    )

    issue_date = models.DateField(
        default=timezone.now,
    )

    due_date = models.DateField()

    return_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="issued",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.book.title} - {self.member.name}"

    def check_overdue(self):
        if (
            self.status == "issued"
            and self.due_date < timezone.now().date()
        ):
            self.status = "overdue"
            self.save(update_fields=["status"])

        return self.status == "overdue"
