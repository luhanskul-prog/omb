from django.urls import path
from . import views


urlpatterns = [

    path(
        "",
        views.parent_dashboard,
        name="parent_dashboard"
    ),

    path(
        "child/<int:student_id>/",
        views.child_portal,
        name="child_portal"
    ),

    path(
        "child/<int:student_id>/fees/",
        views.child_fees,
        name="child_fees"
    ),

]