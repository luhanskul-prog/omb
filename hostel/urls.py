from django.urls import path

from . import views


app_name = "hostel"


urlpatterns = [

    path(
        "",
        views.hostel_dashboard,
        name="dashboard",
    ),

    # HOSTELS
    path(
        "hostels/",
        views.hostels,
        name="hostels",
    ),

    path(
        "hostels/add/",
        views.hostel_create,
        name="hostel_create",
    ),

    path(
        "hostels/<int:pk>/edit/",
        views.hostel_edit,
        name="hostel_edit",
    ),

    # ROOMS
    path(
        "rooms/",
        views.rooms,
        name="rooms",
    ),

    path(
        "rooms/add/",
        views.room_create,
        name="room_create",
    ),

    path(
        "rooms/<int:pk>/edit/",
        views.room_edit,
        name="room_edit",
    ),

    # BEDS
    path(
        "beds/",
        views.beds,
        name="beds",
    ),

    path(
        "beds/add/",
        views.bed_create,
        name="bed_create",
    ),

    path(
        "beds/<int:pk>/edit/",
        views.bed_edit,
        name="bed_edit",
    ),

    # ALLOCATIONS
    path(
        "allocations/",
        views.allocations,
        name="allocations",
    ),

    path(
        "allocations/add/",
        views.allocation_create,
        name="allocation_create",
    ),

    path(
        "allocations/<int:pk>/edit/",
        views.allocation_edit,
        name="allocation_edit",
    ),

    path(
        "allocations/<int:pk>/end/",
        views.allocation_end,
        name="allocation_end",
    ),

    # ATTENDANCE
    path(
        "attendance/",
        views.attendance,
        name="attendance",
    ),

    # FEES
    path(
        "fees/",
        views.fees,
        name="fees",
    ),

    path(
        "fees/add/",
        views.fee_create,
        name="fee_create",
    ),

    path(
        "fees/<int:pk>/edit/",
        views.fee_edit,
        name="fee_edit",
    ),

    path(
        "fees/<int:pk>/paid/",
        views.fee_mark_paid,
        name="fee_mark_paid",
    ),

    # APPLICATIONS
    path("applications/", views.applications, name="applications"),
    path(
        "applications/<int:pk>/approve/",
        views.application_approve,
        name="application_approve",
    ),
    path(
        "applications/<int:pk>/reject/",
        views.application_reject,
        name="application_reject",
    ),
    # INCIDENTS
    path(
        "incidents/",
        views.incidents,
        name="incidents",
    ),

    path(
        "incidents/add/",
        views.incident_create,
        name="incident_create",
    ),

    path(
        "incidents/<int:pk>/edit/",
        views.incident_edit,
        name="incident_edit",
    ),

    path(
        "incidents/<int:pk>/resolve/",
        views.incident_resolve,
        name="incident_resolve",
    ),
]

