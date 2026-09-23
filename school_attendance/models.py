from django.db import models
from students.models import Student


class Attendance(models.Model):

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("EXCUSED", "Excused"),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PRESENT"
    )

    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-date", "student__first_name"]

        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="unique_student_attendance_per_day"
            )
        ]

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.date} - "
            f"{self.status}"
        )