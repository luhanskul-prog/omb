from django.urls import path

from . import views


app_name = "school_attendance"


urlpatterns = [

    # ========================================================
    # ATTENDANCE DASHBOARD
    # /attendance/
    # ========================================================

    path(
        "",
        views.attendance_dashboard,
        name="attendance_dashboard"
    ),


    # ========================================================
    # DAILY ATTENDANCE
    # /attendance/daily/
    # ========================================================

    path(
        "daily/",
        views.daily_attendance,
        name="daily_attendance"
    ),


    # ========================================================
    # ATTENDANCE REPORTS
    # /attendance/reports/
    # ========================================================

    path(
        "reports/",
        views.attendance_reports,
        name="attendance_reports"
    ),


    # ========================================================
    # ATTENDANCE ANALYSIS
    # /attendance/analysis/
    # ========================================================

    path(
        "analysis/",
        views.attendance_analysis,
        name="attendance_analysis"
    ),

]