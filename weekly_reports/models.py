from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from students.models import Student



class WeeklyAssessmentWeek(models.Model):
    academic_year = models.ForeignKey(
        "fees.AcademicYear",
        on_delete=models.PROTECT,
        related_name="weekly_assessment_weeks",
    )
    term = models.ForeignKey(
        "fees.Term",
        on_delete=models.PROTECT,
        related_name="weekly_assessment_weeks",
    )
    week_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=100, blank=True)
    week_start = models.DateField()
    week_end = models.DateField()
    description = models.TextField(blank=True)
    is_locked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_assessment_weeks_created",
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_assessment_weeks_locked",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "term", "week_number"],
                name="unique_weekly_assessment_week",
            )
        ]

    def clean(self):
        errors = {}

        if self.week_end < self.week_start:
            errors["week_end"] = "Week end date cannot be before week start date."

        if not 1 <= self.week_number <= 53:
            errors["week_number"] = "Week number must be between 1 and 53."

        if errors:
            raise ValidationError(errors)

    @property
    def display_title(self):
        return self.title or f"Week {self.week_number}"

    def __str__(self):
        return f"{self.display_title} ({self.week_start} - {self.week_end})"


class WeeklyAssessmentReport(models.Model):
    week = models.ForeignKey(
        "WeeklyAssessmentWeek",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="weekly_assessment_reports",
    )
    subject = models.ForeignKey(
        "timetable.TimetableSubject",
        on_delete=models.PROTECT,
        related_name="weekly_assessment_reports",
    )

    # Snapshot of the learner's class at the time of the report.
    class_name = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, blank=True)

    week_start = models.DateField()
    week_end = models.DateField()
    week_number = models.PositiveSmallIntegerField()

    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=100,
    )

    teacher_report = models.TextField(blank=True)

    is_published = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_reports_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_reports_updated",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-week_start",
            "student__last_name",
            "student__first_name",
            "subject__name",
        ]
        indexes = [
            models.Index(fields=["student", "week_start"]),
            models.Index(fields=["subject", "week_start"]),
            models.Index(fields=["class_name", "week_start"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject", "week_start", "week_end"],
                name="unique_student_subject_weekly_report",
            )
        ]

    def clean(self):
        errors = {}

        if self.week_end < self.week_start:
            errors["week_end"] = "Week end date cannot be before week start date."

        if not 1 <= self.week_number <= 53:
            errors["week_number"] = "Week number must be between 1 and 53."

        if self.max_score is not None and self.max_score <= 0:
            errors["max_score"] = "Maximum score must be greater than zero."

        if self.score is not None:
            if self.score < 0:
                errors["score"] = "Score cannot be negative."
            elif self.max_score is not None and self.score > self.max_score:
                errors["score"] = "Score cannot be greater than maximum score."

        if errors:
            raise ValidationError(errors)

    @property
    def percentage(self):
        if self.score is None or not self.max_score:
            return None
        return round((float(self.score) / float(self.max_score)) * 100, 2)

    def __str__(self):
        return (
            f"{self.student} - {self.subject} - "
            f"Week {self.week_number}"
        )


class WeeklyReportReply(models.Model):
    report = models.ForeignKey(
        WeeklyAssessmentReport,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_report_replies",
    )
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author} - {self.report}"

