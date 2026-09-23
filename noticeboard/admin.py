from django.contrib import admin

from .models import Notice


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "priority",
        "audience",
        "published",
        "publish_date",
        "expiry_date",
        "created_by",
    )

    list_filter = (
        "priority",
        "audience",
        "published",
        "publish_date",
        "expiry_date",
    )

    search_fields = (
        "title",
        "content",
    )

    ordering = (
        "-publish_date",
    )

    readonly_fields = (
        "publish_date",
        "created_at",
        "updated_at",
        "created_by",
    )

    fieldsets = (
        (
            "Notice",
            {
                "fields": (
                    "title",
                    "content",
                    "priority",
                    "audience",
                )
            },
        ),
        (
            "Publishing",
            {
                "fields": (
                    "published",
                    "publish_date",
                    "expiry_date",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )
