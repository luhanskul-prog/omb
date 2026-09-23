from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import AssessmentWindow


@login_required
def assessment_countdown(request):

    windows = (
        AssessmentWindow.objects
        .filter(is_active=True)
        .select_related(
            "academic_year",
            "term",
            "assessment_type",
        )
        .order_by("deadline")
    )

    # Only assessments that are currently recordable.
    open_windows = [
        window
        for window in windows
        if window.recording_open()
    ]

    if not open_windows:
        return JsonResponse({
            "available": False,
            "message": "No assessment is currently open for mark recording.",
        })

    # Nearest closing assessment.
    window = open_windows[0]

    status = "OPEN"

    if window.is_reopened:
        status = "REOPENED"
    else:
        from django.utils import timezone

        remaining_seconds = (
            window.deadline - timezone.now()
        ).total_seconds()

        if remaining_seconds <= 86400:
            status = "CLOSING SOON"

    return JsonResponse({
        "available": True,
        "status": status,
        "deadline": window.deadline.isoformat(),
        "academic_year": str(window.academic_year),
        "term": str(window.term),
        "assessment_type": str(window.assessment_type),
        "assessment_id": window.id,
    })
