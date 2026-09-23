
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class ProfessionalDocument(models.Model):

    TYPE_SCHEME = "SCHEME"
    TYPE_RECORD = "RECORD"
    TYPE_LESSON = "LESSON_PLAN"

    DOCUMENT_TYPES = [
        (TYPE_SCHEME, "Scheme of Work"),
        (TYPE_RECORD, "Record of Work"),
        (TYPE_LESSON, "Lesson Plan"),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_SUBMITTED = "SUBMITTED"
    STATUS_APPROVED = "APPROVED"
    STATUS_FLAGGED = "FLAGGED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_FLAGGED, "Flagged"),
    ]

    academic_year = models.ForeignKey(
        "fees.AcademicYear",
        on_delete=models.PROTECT,
        related_name="professional_documents",
    )

    term = models.ForeignKey(
        "fees.Term",
        on_delete=models.PROTECT,
        related_name="professional_documents",
    )

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPES,
    )

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_documents",
    )

    class_name = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, blank=True)

    subject = models.ForeignKey(
        "timetable.TimetableSubject",
        on_delete=models.PROTECT,
        related_name="professional_documents",
    )

    # Scheme of Work: termly date range
    from_date = models.DateField(
        null=True,
        blank=True,
    )

    to_date = models.DateField(
        null=True,
        blank=True,
    )

    # Records of Work and Lesson Plans: individual lesson timing
    lesson_date = models.DateField(
        null=True,
        blank=True,
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
        blank=True,
    )

    content = models.TextField(
        blank=True,
    )

    uploaded_file = models.FileField(
        upload_to="professional_documents/%Y/%m/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx"]
            )
        ],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_professional_documents",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    admin_remarks = models.TextField(
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
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.get_document_type_display()} - "
            f"{self.teacher} - "
            f"{self.class_name} - "
            f"{self.subject}"
        )

    @property
    def is_editable_by_teacher(self):
        return self.status in [
            self.STATUS_DRAFT,
            self.STATUS_FLAGGED,
        ]

