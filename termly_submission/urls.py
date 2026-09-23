
from django.urls import path

from . import views


app_name = "termly_submission"


urlpatterns = [

    path(
        "staff/",
        views.staff_report,
        name="staff_report",
    ),

    path(
        "admin/requirements/",
        views.admin_requirements,
        name="admin_requirements",
    ),

    path(
        "admin/report/",
        views.admin_report,
        name="admin_report",
    ),
]
