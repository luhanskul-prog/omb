from django.db import models

from students.models import Student
from fees.models import AcademicYear, Term


# ============================================================
# STREAM
# ============================================================

class Stream(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    code = models.CharField(
        max_length=30,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# SUBJECT
# ============================================================

class Subject(models.Model):

    name = models.CharField(
        max_length=100
    )

    code = models.CharField(
        max_length=30,
        unique=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ============================================================
# ASSESSMENT TYPE
# ============================================================

class AssessmentType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    code = models.CharField(
        max_length=30,
        unique=True
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ============================================================
# GRADING SCALE
# ============================================================

class GradingScale(models.Model):

    grade = models.CharField(
        max_length=10
    )

    minimum_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    maximum_score = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    points = models.PositiveIntegerField()

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["-minimum_score"]

    def __str__(self):

        return (
            f"{self.grade} | "
            f"{self.minimum_score}-{self.maximum_score} | "
            f"{self.points} points"
        )


# ============================================================
# ASSESSMENT / MARK
# ============================================================

class Assessment(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="academic_results"
    )

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="academic_results"
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="academic_results"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="assessments"
    )

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="assessments"
    )

    # ========================================================
    # MARK
    # ========================================================

    # ALL MARKS ARE OUT OF 100

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    teacher_comment = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "student",
            "subject",
            "assessment_type",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "academic_year",
                    "term",
                    "subject",
                    "assessment_type",
                ],
                name="unique_student_term_subject_assessment",
            )
        ]

    # ========================================================
    # GRADE
    # ========================================================

    def grade(self):

        grading = (
            GradingScale.objects
            .filter(
                is_active=True,
                minimum_score__lte=self.score,
                maximum_score__gte=self.score,
            )
            .order_by("-minimum_score")
            .first()
        )

        if grading:
            return grading.grade

        return "-"

    # ========================================================
    # POINTS
    # ========================================================

    def points(self):

        grading = (
            GradingScale.objects
            .filter(
                is_active=True,
                minimum_score__lte=self.score,
                maximum_score__gte=self.score,
            )
            .order_by("-minimum_score")
            .first()
        )

        if grading:
            return grading.points

        return 0

    # ========================================================
    # DISPLAY
    # ========================================================

    def __str__(self):

        return (
            f"{self.student} - "
            f"{self.subject} - "
            f"{self.assessment_type} - "
            f"{self.score}/100"
        )

# ============================================================
# ASSESSMENT WINDOW
# ============================================================

class AssessmentWindow(models.Model):

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="assessment_windows"
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
        related_name="assessment_windows"
    )

    assessment_type = models.ForeignKey(
        AssessmentType,
        on_delete=models.PROTECT,
        related_name="assessment_windows"
    )

    deadline = models.DateTimeField()

    warning_minutes = models.PositiveIntegerField(
        default=1440
    )

    is_reopened = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "-deadline",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "academic_year",
                    "term",
                    "assessment_type",
                ],
                name="unique_assessment_window"
            )
        ]

    def __str__(self):

        return (
            f"{self.academic_year} | "
            f"{self.term} | "
            f"{self.assessment_type}"
        )

    def deadline_passed(self):

        from django.utils import timezone

        return (
            timezone.now() >= self.deadline
            and not self.is_reopened
        )

    def recording_open(self):

        return (
            self.is_active
            and not self.deadline_passed()
        )
