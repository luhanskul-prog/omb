from .models import SchoolBranding


def school_branding(request):
    branding = SchoolBranding.objects.first()
    return {
        "branding": branding,
    }
