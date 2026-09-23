
from django.contrib import admin
from .models import ProfessionalDocument


@admin.register(ProfessionalDocument)
class ProfessionalDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "document_type",
        "teacher",
        "class_name",
        "stream",
        "subject",
        "academic_year",
        "term",
        "status",
        "created_at",
    )

    list_filter = (
        "document_type",
        "status",
        "academic_year",
        "term",
        "subject",
        "class_name",
    )

    search_fields = (
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
        "class_name",
        "stream",
        "subject__name",
        "title",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
    )
