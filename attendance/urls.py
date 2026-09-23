from django.urls import path

from . import views


app_name = "attendance"


urlpatterns = [

    # Attendance home
    path(
        "",
        views.attendance_dashboard,
        name="dashboard",
    ),

    # Record attendance
    path(
        "mark/",
        views.mark_attendance,
        name="mark_attendance",
    ),

    # Save attendance
    path(
        "save/",
        views.save_attendance,
        name="save_attendance",
    ),

    # View attendance
    path(
        "view/",
        views.view_attendance,
        name="view_attendance",
    ),

    # Printable report
    path(
        "print/",
        views.print_attendance,
        name="print_attendance",
    ),

    # Class attendance
    path(
        "class/<str:class_name>/",
        views.class_attendance,
        name="class_attendance",
    ),
]