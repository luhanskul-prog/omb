from django.views.generic import RedirectView
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

from django.conf import settings
from django.conf.urls.static import static

from accounts import views as account_views


# =========================================================
# ROOT REDIRECT
# =========================================================

def home_redirect(request):
    """
    Redirect the root URL to the login page.
    """
    return redirect("login")


# =========================================================
# URL PATTERNS
# =========================================================

urlpatterns = [
    path(
        "termly-submission/",
        include("termly_submission.urls"),
    ),

    path(
        "weekly-reports/",
        include("weekly_reports.urls"),
    ),

    path("number-formats/", include("number_formats.urls")),

    # =====================================================
    # HOME
    # =====================================================

    path(
        "",
        home_redirect,
        name="home",
    ),


    # =====================================================
    # DJANGO ADMIN
    # =====================================================

    path(
        "admin/",
        admin.site.urls,
    ),


    # =====================================================
    # AUTHENTICATION
    # =====================================================

    path(
        "login/",
        account_views.login_view,
        name="login",
    ),

    path(
        "logout/",
        account_views.logout_view,
        name="logout",
    ),


    # =====================================================
    # MAIN DASHBOARDS
    # =====================================================

    path(
        "admin-dashboard/",
        account_views.admin_dashboard,
        name="admin_dashboard",
    ),

    path(
        "staff-dashboard/",
        account_views.staff_dashboard,
        name="staff_dashboard",
    ),

    path(
        "student-dashboard/",
        account_views.student_dashboard,
        name="student_dashboard",
    ),

    path(
        "parent-dashboard/",
        account_views.parent_dashboard,
        name="parent_dashboard",
    ),


    # =====================================================
    # ACCOUNTS / USER MANAGEMENT
    # =====================================================

    path(
        "accounts/",
        include("accounts.urls"),
    ),


    # =====================================================
    # HR & PAYROLL
    # =====================================================

    path(
        "hr-payroll/",
        include("hr_payroll.urls"),
    ),


    # =====================================================
    # FEES
    # =====================================================

    path(
        "fees/",
        include("fees.urls"),
    ),


    # =====================================================
    # ACADEMIC
    # =====================================================

    path(
        "academic/",
        include("academic.urls"),
    ),


    # =====================================================
    # TIMETABLING
    # =====================================================

    path(
        "timetable/",
        include("timetable.urls"),
    ),
    # =====================================================
    # LEGACY SCHEDULING URL
    # =====================================================
    path(
        "scheduling/",
        RedirectView.as_view(
            pattern_name="timetable:dashboard",
            permanent=False,
        ),
    ),


    # =====================================================
    # STUDENTS
    # =====================================================

    path(
        "students/",
        include("students.urls"),
    ),


    # =====================================================
    # ATTENDANCE
    # =====================================================

    path(
        "attendance/",
        include("attendance.urls"),
    ),


    # =====================================================
    # TRANSPORT
    # =====================================================

    path(
        "transport/",
        include("transport.urls"),
    ),


    # =====================================================
    # HOSTEL
    # =====================================================

    path(
        "hostel/",
        include("hostel.urls"),
    ),


    # =====================================================
    # INVENTORY
    # =====================================================

    path(
        "inventory/",
        include("inventory.urls"),
    ),


    # =====================================================
    # LIBRARY
    # =====================================================

    path(
        "library/",
        include("library.urls"),
    ),


    # =====================================================
    # NOTICE BOARD
    # =====================================================

    path(
        "noticeboard/",
        include("noticeboard.urls"),
    ),


    # =====================================================
    # MESSAGING
    # =====================================================

    path(
        "messaging/",
        include("messaging.urls"),
    ),


    # =====================================================
    # LMS
    # =====================================================

    path(
        "lms/",
        include("lms.urls"),
    ),

    path("professional-documents/", include("professional_documents.urls")),
]


# =========================================================
# MEDIA FILES
# =========================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

