from django.templatetags.static import static

from accounts.models import SchoolBranding


def school_branding(request):

    branding = (
        SchoolBranding.objects
        .filter(is_active=True)
        .order_by("-id")
        .first()
    )

    logo_url = static("images/LUHANLOGO.jpg")

    if branding and branding.logo:
        try:
            if branding.logo.storage.exists(branding.logo.name):
                logo_url = branding.logo.url
        except Exception:
            pass

    return {
        "branding": branding,
        "branding_logo_url": logo_url,
    }