
from django.conf import settings
from django.db import models


class TermlySubmissionRequirement(models.Model):

    teacher = models.ForeignKey(
        "timetable.TimetableTeacher",
        on_delete=models.CASCADE,
        related_name="termly_submission_requirements",
    )

    academic_year = models.ForeignKey(
        "fees.AcademicYear",
        on_delete=models.PROTECT,
        related_name="termly_submission_requirements",
    )

    term = models.ForeignKey(
        "fees.Term",
        on_delete=models.PROTECT,
        related_name="termly_submission_requirements",
    )

    class_name = models.CharField(max_length=100)

    stream = models.CharField(
        max_length=100,
        blank=True,
    )

    subject = models.ForeignKey(
        "timetable.TimetableSubject",
        on_delete=models.PROTECT,
        related_name="termly_submission_requirements",
    )

    expected_schemes = models.PositiveIntegerField(default=0)

    expected_records = models.PositiveIntegerField(default=0)

    expected_lesson_plans = models.PositiveIntegerField(default=0)

    admin_feedback = models.TextField(blank=True)

    feedback_updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "class_name",
            "stream",
            "subject__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "academic_year",
                    "term",
                    "class_name",
                    "stream",
                    "subject",
                ],
                name="unique_termly_submission_requirement",
            )
        ]

    def __str__(self):
        teacher_name = self.teacher.get_full_name() or self.teacher.username

        return (
            f"{teacher_name} - "
            f"{self.class_name} "
            f"{self.stream} - "
            f"{self.subject}"
        )

    @property
    def total_expected(self):
        return (
            self.expected_schemes
            + self.expected_records
            + self.expected_lesson_plans
        )

