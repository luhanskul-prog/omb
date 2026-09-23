from django.contrib.auth.decorators import login_required
from accounts.staff_access import role_permission_required
from django.shortcuts import render

from .models import (
    Vehicle,
    Driver,
    Route,
    StudentTransportAssignment,
    TransportTrip,
    FuelRecord,
    VehicleMaintenance,
)


# =========================================================
# TRANSPORT DASHBOARD
# =========================================================

@login_required
@role_permission_required("view_vehicle", "transport")
def transport_dashboard(request):
    """
    Main Transport Management Dashboard.
    """

    # =====================================================
    # BASIC COUNTS
    # =====================================================

    total_vehicles = Vehicle.objects.count()

    total_drivers = Driver.objects.count()

    total_routes = Route.objects.count()

    total_assignments = (
        StudentTransportAssignment.objects.count()
    )

    total_trips = TransportTrip.objects.count()


    # =====================================================
    # VEHICLE STATUS
    # =====================================================

    active_vehicles = Vehicle.objects.filter(
        status="active"
    ).count()

    inactive_vehicles = Vehicle.objects.exclude(
        status="active"
    ).count()


    # =====================================================
    # RECENT VEHICLES
    # =====================================================

    vehicles = Vehicle.objects.all().order_by(
        "-id"
    )[:6]


    # =====================================================
    # RECENT DRIVERS
    # =====================================================

    drivers = Driver.objects.all().order_by(
        "-id"
    )[:6]


    # =====================================================
    # RECENT ROUTES
    # =====================================================

    routes = Route.objects.all().order_by(
        "-id"
    )[:6]


    # =====================================================
    # RECENT TRIPS
    # =====================================================

    trips = TransportTrip.objects.all().order_by(
        "-id"
    )[:6]


    # =====================================================
    # FUEL RECORDS
    # =====================================================

    fuel_records = FuelRecord.objects.all().order_by(
        "-id"
    )[:5]


    # =====================================================
    # MAINTENANCE RECORDS
    # =====================================================

    maintenance_records = (
        VehicleMaintenance.objects.all().order_by(
            "-id"
        )[:5]
    )


    # =====================================================
    # DASHBOARD CONTEXT
    # =====================================================

    context = {

        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "inactive_vehicles": inactive_vehicles,

        "total_drivers": total_drivers,

        "total_routes": total_routes,

        "total_assignments": total_assignments,

        "total_trips": total_trips,

        "vehicles": vehicles,

        "drivers": drivers,

        "routes": routes,

        "trips": trips,

        "fuel_records": fuel_records,

        "maintenance_records": maintenance_records,
    }


    # =====================================================
    # RENDER DASHBOARD
    # =====================================================

    return render(
        request,
        "transport/transport_dashboard.html",
        context,
    )