from accounts.models import SchoolBranding


def school_branding(request):

    branding = (
        SchoolBranding.objects
        .filter(is_active=True)
        .order_by("-id")
        .first()
    )

    return {
        "branding": branding,
    }