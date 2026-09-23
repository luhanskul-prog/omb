
from django.urls import path
from . import views
from . import staff_write
from . import admin_write

app_name = "weekly_reports"

urlpatterns = [
    path("staff/write/", staff_write.staff_write, name="staff_write"),
    path("staff/write/individual/", staff_write.staff_write_individual, name="staff_write_individual"),
    path("staff/write/class/", staff_write.staff_write_class, name="staff_write_class"),
    path("admin/write/", admin_write.admin_write, name="admin_write"),
    path("admin/write/individual/", admin_write.admin_write_individual, name="admin_write_individual"),
    path("admin/write/class/", admin_write.admin_write_class, name="admin_write_class"),

    path("manage-weeks/", views.manage_weeks, name="manage_weeks"),
    path("weeks/add/", views.week_create, name="week_create"),
    path("weeks/<int:pk>/edit/", views.week_edit, name="week_edit"),
    path("weeks/<int:pk>/lock/", views.week_lock, name="week_lock"),
    path("weeks/<int:pk>/unlock/", views.week_unlock, name="week_unlock"),

    path("dashboard/", views.reports_dashboard, name="dashboard"),
    path("admin/", views.admin_reports, name="admin_reports"),
    path("staff/", views.staff_reports, name="staff_reports"),
    path("student/", views.student_reports, name="student_reports"),
    path("parent/", views.parent_reports, name="parent_reports"),
    path("create/", views.report_create, name="create"),
    path("<int:pk>/edit/", views.report_edit, name="edit"),
    path("<int:pk>/reply/", views.report_reply, name="reply"),
    path("<int:pk>/", views.report_detail, name="detail"),
]
